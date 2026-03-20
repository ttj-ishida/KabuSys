CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。  

0.1.0 (2026-03-20)
------------------

初回リリース — KabuSys 0.1.0 を公開します。本リリースは日本株自動売買システムの基礎機能群を実装しています。主要な追加点、設計上の注意点、セキュリティ対策、既知の制限を以下に示します。

Added
- 基本パッケージ
  - パッケージバージョン __version__ = "0.1.0" を設定。
  - 公開モジュール: data, strategy, execution, monitoring（__all__ を定義）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み（優先順: OS 環境変数 > .env.local > .env）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - プロジェクトルート探索: .git または pyproject.toml を基準に自パッケージ位置から探索（CWD に依存しない）。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理など堅牢な解析を実装。
  - Settings クラス: 必須キー取得（_require）、値検証（KABUSYS_ENV／LOG_LEVEL の許容値チェック）、各種プロパティを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境判定ユーティリティなど）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限制御: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - リトライ・バックオフ: 指数バックオフ、最大 3 回、408/429/5xx に対する再試行、429 の場合は Retry-After を考慮。
  - 401 ハンドリング: トークン期限切れ時に自動でリフレッシュして 1 回再試行（無限再帰対策の allow_refresh フラグあり）。
  - ID トークンのモジュールレベル・キャッシュ（ページネーション間で共有）。
  - ページネーション対応のデータ取得: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE による upsert、fetched_at を UTC で記録）。
  - データ整形ユーティリティ: _to_float / _to_int（文字列や欠損値に対する安全変換）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news へ冪等保存するための基盤を実装。
  - URL 正規化: トラッキングパラメータ（utm_* 等）の除去、クエリキーソート、スキーム/ホスト小文字化、フラグメント削除。
  - セキュリティ対策: defusedxml を使用して XML 攻撃を防止、HTTP/HTTPS のみ許可して SSRF を抑止、最大受信サイズ（10MB）でメモリDoS を緩和。
  - バルク挿入のチャンク処理や SHA-256 による記事 ID 生成による冪等性設計（ID は正規化 URL 等に基づくハッシュを利用する方針）。
  - （注）ファイル内の一部実装は続きがある設計になっており、以降のマッピング/銘柄紐付け処理等は本リリースで組み込まれている箇所と今後の拡張箇所が混在。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離（MA200）、ウィンドウ不足時の None ハンドリングを SQL ウィンドウ関数で実装。
    - calc_volatility: 20日 ATR（true range を厳密に扱う）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を算出。ウィンドウ不足時は None。
    - calc_value: raw_financials の最新財務データ（target_date 以前）と prices_daily を組み合わせて PER/ROE を算出（EPS=0 の場合は None）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算。horizons の検証（正の整数 ≤ 252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。サンプル不足（<3）やゼロ分散時は None。
    - factor_summary: カラム別の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクで処理（丸めによる tie 検出対策として round(v, 12) を使用）。
  - これらを研究用 API として公開（kabusys.research.__all__）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research の生ファクターを取得しマージ。
    - ユニバースフィルタ: 最低株価 300 円、20日平均売買代金 >= 5 億円でフィルタリング。
    - 正規化: zscore_normalize を適用し ±3 でクリップ。
    - features テーブルへ日付単位で置換（削除→挿入）しトランザクションで原子性を担保。
    - 処理はルックアヘッドバイアスを避ける設計（target_date 時点のデータのみを使用）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - スコア変換: Z スコア → シグモイド関数（0..1）への変換、欠損コンポーネントは中立 0.5 で補完。
    - 重み付け: デフォルト重みを提供し、ユーザー重みは検証・正規化して合計 1.0 に再スケール。
    - Bear レジーム検出: ai_scores の regime_score の平均が負（サンプル数閾値あり）で BUY を抑制。
    - BUY シグナル閾値デフォルト 0.60。
    - SELL 判定: ストップロス（終値 / avg_price - 1 <= -8%）優先、final_score が閾値未満の銘柄を SELL（positions / latest price を参照）。価格欠損時は判定をスキップして誤クローズを回避。
    - signals テーブルへ日付単位置換（トランザクション＋バルク挿入）。
    - シグナル生成のログと冪等性を重視。

- 公開 API の整理
  - strategy/__init__.py で build_features / generate_signals を再公開。
  - research/__init__.py で主要ユーティリティを公開。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Security
- XML パースに defusedxml を採用して XML 関連の攻撃（XML Bomb 等）を緩和。
- RSS URL の正規化とトラッキングパラメータ除去、HTTP/HTTPS のみ受け入れる仕様で SSRF リスクを低減。
- HTTP クライアント実装でタイムアウト・受信サイズ上限・再試行ポリシーを導入し、外部依存の脆弱性やサービス拒否を緩和。
- J-Quants の 401 リフレッシュ処理は allow_refresh フラグで制御し、無限再帰を防止。

Performance / Reliability
- DuckDB への保存はバルク挿入・トランザクション・ON CONFLICT upsert を用いて性能と冪等性を向上。
- API 呼び出しは固定間隔スロットリングでレート制限を厳守。
- ID トークンをページネーション間でキャッシュし不要な再認証を抑制。

Database / Schema（期待されるテーブル）
- raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news などを前提とした処理を実装。各関数は該当テーブルの存在を前提とします。

Known limitations / Notes
- SELL の一部ロジック（トレーリングストップや時間決済など）は positions テーブルに peak_price / entry_date 等の追加カラムが必要であり、現バージョンでは未実装で注記あり。
- news_collector は記事→銘柄紐付け（news_symbols など）や一部の細かな処理が設計に記載されているが、今後の拡張で強化予定。
- 一部の入力検証・境界条件は厳密に扱っているが、実運用前に実データでの検証を推奨（特に欠損データや市場休日など）。
- DuckDB を利用するため、対応する DB スキーマ作成・マイグレーションは別途用意する必要があります。

Compatibility / Breaking Changes
- 初回リリースのため破壊的変更はありません。今後のバージョンで API 変更が生じる可能性があります。

開発者向けメモ
- 自動読み込みされる環境変数の例は .env.example を参照して設定してください（必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
- テスト時に自動 .env 読み込みを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベルや実運用モード（development / paper_trading / live）は環境変数 KABUSYS_ENV / LOG_LEVEL で制御します。

今後の TODO / 予定
- news_collector の銘柄マッチング/自然言語処理連携の強化。
- ポジション管理（positions）に peak_price / entry_date 等を追加してトレーリングストップ・時間決済を実装。
- execution 層（kabu ステーション連携）の実装と監視（monitoring）周りの強化。
- 詳細なテスト・フェイルセーフ（特に外部 API 障害時の挙動）を追加。

以上。