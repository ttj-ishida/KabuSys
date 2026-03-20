# CHANGELOG

すべての変更は「Keep a Changelog」形式に従います。  
これは初回リリース (v0.1.0) をコードベースから推測してまとめた変更履歴です。

全般
- 初期バージョン: 0.1.0
- パッケージ名: kabusys
- 目的: 日本株の自動売買支援ライブラリ（データ取得、研究用ファクター計算、特徴量作成、シグナル生成、DuckDB 保存など）

[Unreleased]
- （今後の変更をここに記載）

[0.1.0] - 2026-03-20
Added
- パッケージ基盤
  - src/kabusys/__init__.py によるパッケージ初期化とバージョン定義（__version__ = 0.1.0）。
  - パブリック API を示す __all__（data, strategy, execution, monitoring）。

- 環境設定
  - src/kabusys/config.py:
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
    - 行パーサは export KEY=val、クォート処理、インラインコメントの取り扱いをサポート。
    - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 環境変数上書き制御（override と protected セットによる保護）。
    - 必須環境変数取得のヘルパー _require と Settings クラス（J-Quants / kabu / Slack / DB パス / システム設定）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック。
    - デフォルトの DB パス（duckdb/sqlite）や kabu API の既定値。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアント実装（認証、ページネーション、取得 API 用関数）。
    - レートリミッタ（固定間隔スロットリング、120 req/min）。
    - リトライ戦略（指数バックオフ、最大試行回数、408/429/5xx の再試行、Retry-After 優先）。
    - 401 応答時のトークン自動リフレッシュ（1 回のみ）と無限再帰防止フラグ allow_refresh。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
      - ON CONFLICT を利用した更新による冪等性。
      - fetched_at を UTC ISO8601 で記録（Look-ahead バイアス追跡）。
      - 入力値を安全に float/int に変換するユーティリティ（_to_float, _to_int）。
      - PK 欠損行のスキップとログ出力。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を取得して raw_news へ保存する処理方針とユーティリティ。
    - デフォルト RSS ソースを定義（Yahoo Finance のカテゴリ RSS）。
    - セキュリティ対策: defusedxml を用いた XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）、URL 正規化（トラッキングパラメータ除去）、スキームチェック（HTTP/HTTPS のみ想定）、SSRF を考慮した保護。
    - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成して冪等性を確保。
    - バルク INSERT のチャンク化で DB 負荷を抑える設計。

- Research（ファクター計算・解析）
  - src/kabusys/research/factor_research.py:
    - モメンタム（calc_momentum）: 1M/3M/6M リターン / 200 日移動平均乖離率（ma200_dev）。
    - ボラティリティ（calc_volatility）: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - バリュー（calc_value）: raw_financials の最新財務データに基づく PER と ROE（EPS が不適切な場合は None）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、営業日不連続（祝日等）を考慮したスキャン範囲バッファを採用。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを計算。
    - IC（calc_ic）: factor と将来リターンのスピアマンランク相関（Spearman ρ）を実装。サンプル不足時の None ハンドリング。
    - ランク付けユーティリティ（rank）およびファクターの統計サマリー（factor_summary）。
    - 外部依存（pandas 等）を使わず標準ライブラリと DuckDB で実装。

- Strategy（特徴量作成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py:
    - build_features: research の生ファクターを読み込み、ユニバースフィルタ適用（最低株価 300 円、20 日平均売買代金 5 億円）、指定カラムを Z スコア正規化、±3 でクリップして features テーブルへ日付単位で UPSERT（トランザクションによる原子性）。
    - 正規化列とフィルタの明示、欠損データに対する扱い。
  - src/kabusys/strategy/signal_generator.py:
    - generate_signals:
      - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - スコアの sigmoid 変換、欠損コンポーネントは中立 (0.5) で補完。
      - デフォルト重みのマージとユーザ入力重みの検証・再スケール（合計が 1.0 になるよう調整）。
      - Bear レジーム判定（ai_scores の regime_score の平均が負なら BUY 抑制。サンプル数閾値あり）。
      - BUY シグナルは閾値 (default 0.60) 超えで付与。SELL は保有ポジションに対するストップロス（-8% 以下）またはスコア低下で生成。
      - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位の置換（トランザクションで原子性）。
      - 未実装だが設計に記載されたエグジット（トレーリングストップ、時間決済）は TODO として明記。

- パッケージ公開 API
  - src/kabusys/strategy/__init__.py で build_features / generate_signals をエクスポート。
  - src/kabusys/research/__init__.py で主な研究用関数をエクスポート。

Changed
- （初版のため変更履歴はなし）

Fixed
- （初版のため修正履歴はなし）

Deprecated
- （初版のため非推奨項目なし）

Removed
- （初版のため削除項目なし）

Security
- ニュース収集: defusedxml の使用、受信サイズ制限、URL 正規化・トラッキング削除、HTTP/HTTPS 限定など複数の安全対策を実装。
- J-Quants クライアント: トークン再取得時の無限再帰防止フラグ（allow_refresh）やレート制御、Retry-After 尊重などの堅牢化。

Notes / Known limitations / TODO
- シグナルのエグジット条件の一部（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date が必要。
- execution / monitoring パッケージは空の名前空間として存在する（発注層やモニタリングは別実装を想定）。
- DuckDB スキーマ（テーブル定義）はこのコードスニペットに含まれていないため、実行前に適切なスキーマ準備が必要。
- 一部の関数は欠損データを許容して None を返す設計（欠損に強い設計だが、利用側での扱いに注意）。

今後の提案（参考）
- trailing stop / time-based exit の実装（positions に peak_price / entry_date を保持）。
- ニュース→銘柄マッチングロジック（news_symbols）の具体実装とテスト強化。
- DuckDB スキーマ定義・移行スクリプトと、エンドツーエンドの統合テスト追加。

--- 
（この CHANGELOG は現状のソースコードから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。）