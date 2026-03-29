# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティックバージョニングを使用しています。  

## [0.1.0] - 2026-03-29

初回リリース。

### Added
- パッケージのエントリポイントを追加
  - src/kabusys/__init__.py にてバージョン (__version__ = "0.1.0") と公開サブパッケージを定義（data, strategy, execution, monitoring）。

- 環境変数・設定管理
  - src/kabusys/config.py
    - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を基準に探索）。これにより CWD に依存せず .env 自動ロードが可能。
    - .env/.env.local の自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env ファイルパーサを実装。以下に対応：
      - コメント行、空行の無視
      - export KEY=val 形式
      - シングル/ダブルクォート内のエスケープ処理
      - クォートなしの場合のインラインコメント判定（直前がスペース/タブの '#' をコメント扱い）
    - 必須環境変数取得ヘルパ（_require）と Settings クラスを提供。J-Quants/OpenAI/Slack/DB など主要設定をプロパティ経由で取得し、適切なバリデーション（例: KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を行う。
    - デフォルトパス（DuckDB/SQLite）や env 判定ユーティリティ（is_live/is_paper/is_dev）を実装。

- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントを算出する機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - 1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、バッチサイズ（_BATCH_SIZE）を導入しトークン肥大化を抑制。
    - JSON Mode を用いた厳密なレスポンス検証と復元ロジック（前後に余計なテキストが混入した場合の {} 抽出）。
    - リトライ（429, ネットワーク, タイムアウト, 5xx）を指数バックオフで実装。非リトライエラーはスキップして処理継続（フェイルセーフ）。
    - スコアを ±1.0 にクリップ。DuckDB への書き込みは部分失敗時に既存データを保護するため、対象コードだけを DELETE → INSERT（冪等操作）で更新。
    - DuckDB 0.10 の executemany の空リスト制約に対応するチェックを実装。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - prices_daily からの MA200 比率計算、raw_news からのマクロキーワードでの抽出、OpenAI でのマクロセンチメント評価、スコア合成と market_regime への冪等書き込みを行う。
    - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックして継続するフェイルセーフ設計。
    - OpenAI 呼び出しは専用の内部ラッパーを使い、モジュール間でプライベート関数を共有しない設計（テスト容易性のため差し替え可能）。

- Data（ETL / カレンダー管理 / J-Quants連携）
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass による ETL 実行結果表現を追加（取得件数・保存件数・品質問題リスト・エラー一覧などを含む）。
    - 差分取得、バックフィル、品質チェックの設計方針を実装（J-Quants クライアント経由の差分取得・idempotent 保存・品質チェックの収集方式）。
    - DuckDB 上での最大日付取得等のユーティリティを追加。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポートし外部公開インターフェースを提供。
  - src/kabusys/data/calendar_management.py
    - market_calendar を利用した営業日判定機能を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合の曜日ベースのフォールバックを実装（カレンダーがまばらでも一貫した判定を返す）。
    - calendar_update_job により J-Quants からの差分フェッチと market_calendar への冪等保存を実装。バックフィル、健全性チェック（未来日付の異常検出）を備える。
    - _table_exists / _has_calendar_data 等のユーティリティを追加。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ（ATR）、バリュー（PER/ROE）等の定量ファクター計算を SQL + Python で実装（prices_daily / raw_financials を参照）。
    - データ不足時の None 戻しや、200行未満での ma200_dev None 扱い等の安全措置を実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク化ユーティリティ rank、統計サマリー factor_summary を実装。
    - 外部依存（pandas 等）を使わず標準ライブラリと DuckDB のみで実装。rank は同順位を平均ランクで扱う。
  - src/kabusys/research/__init__.py
    - 主要関数の再エクスポートを設定（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- （初回リリースにつき該当なし）

### Notes / 開発者向け注意事項
- OpenAI API:
  - デフォルトモデルは gpt-4o-mini。API キーは関数引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照する。未設定の場合は ValueError を送出する箇所あり。
  - LLM レスポンスは JSON モードを前提とするが、前後に余計なテキストが混入するケースを復元して処理するロジックを備える。
  - ネットワーク／レート制限／サーバーエラーに対しては指数バックオフのリトライを行い、最終的に失敗した場合はスキップしてフェイルセーフで継続する。
- データベース（DuckDB）:
  - 書き込みは基本的に冪等（DELETE → INSERT パターン）で実装。部分失敗時に既存データを保護する設計。
  - DuckDB 0.10 の executemany が空リストを受け付けない制約に対するガードを実装している。
- 環境変数自動ロード:
  - 自動ロードはパッケージ import 時に実行される（ただしプロジェクトルートが見つからない場合はスキップ）。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- ルックアヘッドバイアス対策:
  - 全ての「日付に依存する」処理（ニュース窓、ファクター計算、レジーム判定など）は内部で datetime.today()/date.today() を直接参照しない（target_date を明示的に受け取る設計）。これにより将来情報の漏洩を防止。

今後のリリースで予定している改善点（例）
- strategy / execution / monitoring サブパッケージの具体的な実装とテストカバレッジの追加。
- J-Quants クライアントの詳細実装・エラーハンドリングの強化。
- 性能向上（大規模データに対する DuckDB クエリ最適化、OpenAI のバッチ戦略改善）。
- 単体テスト・統合テストの追加と CI ワークフローの整備。