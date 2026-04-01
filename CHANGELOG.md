# Changelog

すべての変更は Keep a Changelog の慣習に従います。  
安定性・後方互換性に関するポリシーは各リリースノートの注記を参照してください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-01

初回公開リリース。以下の主要機能・実装を含みます。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理 (.env / 環境変数)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装（src/kabusys/config.py）。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に検索（CWD 非依存）。
  - .env パーサ実装（エクスポート形式、クォート・エスケープ、インラインコメント処理対応）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 設定取得用 Settings クラスを提供し、必須設定の検査（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）と値バリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - ファイルパスや閾値等のデフォルト値を提供（duckdb/sqlite パス、監視閾値、PID ファイルなど）。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインの結果表現 ETLResult（dataclass）を実装（src/kabusys/data/pipeline.py、src/kabusys/data/etl.py で公開）。
    - 取得件数、保存件数、品質問題、エラーメッセージを保持。has_errors / has_quality_errors / to_dict を提供。
  - マーケットカレンダー管理モジュールを実装（src/kabusys/data/calendar_management.py）。
    - 営業日判定(is_trading_day)、前後営業日取得(next_trading_day / prev_trading_day)、期間内営業日取得(get_trading_days)、SQ 日判定(is_sq_day) を提供。
    - DB に market_calendar がない場合は曜日ベースのフォールバック（週末を非営業日）を使用。
    - calendar_update_job により J-Quants から差分取得・冪等保存を行う処理を実装（バックフィル、健全性チェック含む）。
  - DuckDB 互換性や安全性を考慮したユーティリティ実装（テーブル存在確認、日付変換等）。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメント集約・スコアリングモジュールを実装（src/kabusys/ai/news_nlp.py）。
    - target_date に対応するニュースウィンドウ計算(calc_news_window)。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）に JSON Mode でバッチ送信して銘柄別スコアを取得。
    - 1チャンク当たり最大銘柄数、記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーションと ±1.0 クリップ。取得スコアを ai_scores テーブルへ部分置換（DELETE → INSERT）して部分失敗時の既存データ保護を実現。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch 用の分離実装）。
  - 市場レジーム判定モジュールを実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を決定。
    - prices_daily, raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API エラーやパース失敗に対するフェイルセーフ（macro_sentiment = 0.0）やリトライロジックを実装。
    - OpenAI クライアントは直接生成（api_key 引数または環境変数 OPENAI_API_KEY を使用）。モデルは gpt-4o-mini、JSON レスポンスを要求。
    - ルックアヘッドバイアス防止のため日付参照方法に注意（内部で date.today() を使わない、DB クエリは target_date 未満条件など）。

- リサーチ / ファクター計算
  - factor_research モジュールを実装（src/kabusys/research/factor_research.py）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - Value: PER / ROE（raw_financials から最新財務データを取得）。
    - DuckDB SQL による効率的計算、データ不足時の None 処理。
  - feature_exploration モジュールを実装（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算(calc_forward_returns)（デフォルト horizons=[1,5,21]、horizons バリデーションあり）。
    - IC（Information Coefficient）計算（Spearman の ρ）calc_ic。
    - ランク化ユーティリティ rank（同順位は平均ランク）、統計サマリー factor_summary（count/mean/std/min/max/median）。
    - pandas 等に依存せず標準ライブラリのみで実装。

- 内部ユーティリティ / 安全対策
  - DuckDB のバージョン差異に配慮した実装（executemany に空リストを渡さない等のワークアラウンド）。
  - JSON レスポンスの堅牢なパース（前後に余計なテキストが混ざるケースに対する {} 抽出復元）。
  - 詳細なログ出力（info/debug/warning/exception）を各処理に追加。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし（実装段階で既知のフェールセーフや互換性対策を多数導入）。

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する方式を採用。環境変数の自動読み込みは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Implementation details
- ルックアヘッドバイアス対策: AI 評価やファクター計算はすべて target_date を明示的に受け取り、現在日時参照（date.today()/datetime.today()）を行わない設計。
- OpenAI 呼び出し (gpt-4o-mini) は JSON Mode を前提とするが、実運用では API 応答の不確実性に備えたパース/バリデーションとフォールバックを重視。
- DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 期待の実装箇所等）。部分失敗が起きても既存データを不必要に削除しない工夫を実装。
- テストしやすさを考慮し、OpenAI 呼び出し箇所をモック差替えしやすいよう分離している（ユニットテスト向けフックあり）。

---

今後リリースでは、strategy / execution / monitoring の具象実装（バックテスト・発注ロジック・監視エージェント）、より詳細な品質チェック・メトリクス、CI/デプロイ関連の改善などを予定しています。