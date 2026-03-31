CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
主な変更点はコードベース（src/kabusys 以下）から推測して記載しています。

Unreleased
----------
- なし

[0.1.0] - 2026-03-31
--------------------
初期リリース。パッケージ名: kabusys（日本株自動売買システム）  
本リリースではデータ取得・前処理、研究用ファクター計算、AI を用いたニュース／市場レジーム判定の基盤機能を提供します。

Added
- パッケージ基盤
  - パッケージのバージョンを追加: __version__ = "0.1.0"。
  - kabusys パッケージの公開APIを定義（data, strategy, execution, monitoring を __all__ に登録）。（strategy/execution/monitoring は将来的な実装を想定）
- 環境設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env / .env.local の読み込み順序を管理（OS 環境変数 > .env.local > .env）。
  - export KEY=val 形式やクォート/エスケープ、インラインコメントの扱いに対応した .env パーサーを実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）等の getter を提供。未設定の必須環境変数に対しては ValueError を送出。
- データ関連（kabusys.data）
  - calendar_management: JPX カレンダー管理・営業日判定APIを実装
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar テーブルがない場合は曜日（土日）によるフォールバックを行う設計。
    - カレンダーをJ-Quantsから差分取得する calendar_update_job を実装（バックフィル・健全性チェックあり）。
  - pipeline / ETL: ETL の結果を表す dataclass ETLResult を実装・公開（etl モジュールから再エクスポート）。
    - 差分取得・バックフィル・品質チェックのための設計が反映されたインターフェース（詳細実装は jquants_client / quality モジュールに依存）。
- AI 関連（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む処理を実装。
    - バッチ送信（最大 20 銘柄/チャンク）、スコアのクリッピング、レスポンス検証、リトライ（429/ネットワーク/5xx）を備える。
    - calc_news_window でニュース収集ウィンドウ（JST基準）を正確に算出。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api の patch を想定）。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を生成し、market_regime テーブルへ冪等書き込みする処理を実装。
    - prices_daily / raw_news を参照して MA 計算・マクロ記事抽出・OpenAI 呼び出し・合成スコア化を行う。
    - API エラー時のフェイルセーフ（macro_sentiment = 0.0）やリトライ・ログ出力を実装。
- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、ATR 比、平均売買代金、出来高比などのボラティリティ / 流動性指標を計算。
    - calc_value: raw_financials から取得した最新財務データと株価から PER / ROE を計算（EPS = 0 や欠損時は None）。
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照し外部発注等にアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）までの将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算（欠損や少数サンプルをハンドル）。
    - rank: 同順位の平均ランク処理を含むランク変換。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算する統計サマリを提供。
- DuckDB 利用
  - 主要なデータ処理は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、SQL と Python の組合せで実装。
- テスト・堅牢性向上
  - API 呼び出し箇所は差し替えを想定した設計（単体テストでのモック化容易）。
  - DB 書き込みは冪等性（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）を意識して実装。
  - リトライ・バックオフ、ログ出力、入力バリデーションを多用。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数管理により機密情報（OpenAI APIキー等）は Settings を通じて取得。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / 既知の制限・移行メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティ参照時に必須）
  - OpenAI API キーは news_nlp.score_news / regime_detector.score_regime にて api_key 引数または環境変数 OPENAI_API_KEY が必要
- DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が前提。これらのテーブル定義は別途用意する必要があります。
- __all__ に strategy, execution, monitoring が登録されていますが、今回提供されたコードにはこれらの実装は含まれていません（将来実装予定のプレースホルダ）。
- calendar_update_job や ETL パイプラインは jquants_client / quality モジュールに依存します。実行時にはそのクライアント実装が必要です。
- news_nlp と regime_detector は OpenAI JSON mode（response_format={"type":"json_object"}）を前提とし、出力が不正な場合はフェイルセーフでスコアをスキップまたは 0.0 にフォールバックします。
- 一部ファイル（pipeline の最後など）に切り取り/途中のように見える箇所があります。実行前に該当ファイルの完全性を確認してください。

今後の予定（推測）
- strategy / execution / monitoring モジュールの実装（自動売買ロジック・発注連携・稼働監視）
- テストカバレッジ強化と CI の追加
- DB スキーマ定義・マイグレーションツールの提供

貢献・問い合わせ
- この CHANGELOG はソースコードから機能を推測して記載しています。実際の運用手順や追加の設定項目は README やドキュメントを参照してください。必要であれば、実装の詳細やリリースノートの補足を作成します。