Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - Python パッケージエントリポイントを定義（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 自動ロードの優先順: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ の親を辿り、.git または pyproject.toml を基準に判定（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート対応、バックスラッシュによるエスケープ対応、インラインコメント処理。
    - 不正行はスキップ。
  - 環境変数取得ヘルパー _require と Settings クラスを提供:
    - 必須設定の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - パス指定での DB ファイル（DUCKDB_PATH, SQLITE_PATH）取得。
    - KABUSYS_ENV と LOG_LEVEL の妥当性検証（許容値の定義）。
    - is_live / is_paper / is_dev のブールヘルパー。

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - レート制限の遵守（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。リトライ対象は 408/429/5xx、429 の場合は Retry-After ヘッダ優先。
    - 401 応答時はリフレッシュトークンで id_token を自動更新して 1 回リトライ（再帰防止）。
    - ページネーション対応で全ページを取得。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、look-ahead bias の検査が可能。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT（Upsert）で重複更新を行い冪等性を確保。
    - 入力データの変換ユーティリティ（_to_float, _to_int）を用意。
    - PK 欠損行はスキップし、スキップ件数をログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュールを実装（デフォルトソースに Yahoo Finance を含む）。
  - セキュリティ考慮:
    - defusedxml を使用して XML 攻撃（XML bomb 等）を防止。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）でメモリDoSを抑制。
    - HTTP/HTTPS スキームのみ許可（SSRF 対策の設計方針）。
  - URL 正規化機能を実装:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）除去、スキーム/ホスト小文字化、クエリソート、フラグメント削除。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を使用し冪等性を保証。
  - DB 保存はバルク挿入（チャンク化）かつトランザクションで処理し、実際に挿入された件数を返す設計。

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を計算（200日移動平均はデータ不足時に None を返す）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）を計算。true_range の NULL 伝播を適切に扱い ATR を計算。
    - Value（per, roe）を raw_financials と prices_daily を組み合わせて計算（EPS が 0/欠損時は per=None）。
    - SQL ベースで DuckDB のウィンドウ関数を活用しパフォーマンスを意識した実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（複数ホライズン対応、horizons の検証）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
    - 独自ランク関数 rank（同順位を平均ランクで処理、丸めで ties を安定化）。
  - research パッケージのエクスポートを整備（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize を公開）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features を実装:
    - research モジュールからの生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターを zscore_normalize（kabusys.data.stats 経由）で正規化し ±3 でクリップ（外れ値抑制）。
    - features テーブルへ日付単位で置換（DELETE してから INSERT、トランザクションで原子性確保）。
    - ルックアヘッドバイアスを避けるため target_date 時点のデータのみ使用。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals を実装:
    - features と ai_scores を統合して各銘柄の component score（momentum / value / volatility / liquidity / news）を計算。
    - コンポーネントはシグモイド変換（zスコア → [0,1]）し、欠損値は中立 0.5 で補完。
    - final_score を重み付き合算で算出（デフォルト重みは momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
    - デフォルト BUY 閾値は 0.60。weights は入力で部分指定可、既知キーのみ受け付け、合計が 1.0 になるよう再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合に BUY を抑制。
    - SELL（エグジット）判定を実装:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先で判定。
      - final_score が閾値未満のときスコア低下で SELL。
      - 価格欠損時は SELL 判定をスキップし誤クローズを防止。
      - positions テーブルから最新ポジションを参照。
    - SELL 優先ポリシー: SELL 対象は BUY から除外、BUY のランクを再付与。
    - signals テーブルへ日付単位で置換（トランザクションで原子性確保）。
  - デフォルトの一連の設計は StrategyModel.md の各セクション（記述に基づく）に従う実装方針。

Changed
- （初版のため変更履歴なし）

Fixed
- （初版のため修正履歴なし）

Removed
- （初版のため削除履歴なし）

Security
- RSS 解析に defusedxml を採用し XML ベース攻撃を防止。
- news_collector で受信サイズ上限を設定しメモリ DoS を軽減。
- J-Quants クライアントで SSRF/不正 URL を直接受けない設計（ニュース収集で HTTP/HTTPS スキームのみ許可）。
- 環境変数読み込みはプロジェクトルート検出に基づくため、誤ったパスからの設定読み込みを抑止。

Known limitations / TODO
- strategy の一部仕様が未実装:
  - トレーリングストップ（peak_price 等を管理する positions 側のデータが未整備）
  - 時間決済（保有 60 営業日超過の自動決済）
- バリューファクターの一部（PBR、配当利回り）は未実装。
- news_symbols（記事と銘柄の紐付けロジック）は実装の記述はあるが、紐付けアルゴリズム詳細は要実装/拡張予定。
- 外部依存（DuckDB テーブル定義、Slack や kabu ステーション等の実運用インテグレーション）は本リポジトリ外でのセットアップが必要。

補足
- 多くの DB 書き込み処理は冪等（ON CONFLICT / 日付単位の置換）かつトランザクションで原子性を担保する設計です。
- 研究用関数は外部ライブラリ（pandas 等）に依存せず、標準ライブラリと DuckDB の SQL 機能で実装されています。

README / ドキュメント
- 各モジュールの docstring に設計方針・処理フロー・注意点を記載しています。実運用にあたっては docstring に従い DB スキーマや環境変数を準備してください。