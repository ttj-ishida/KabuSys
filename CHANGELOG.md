# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」準拠です。  
このプロジェクトはセマンティックバージョニングに従います: https://semver.org/

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys のトップレベルモジュール (src/kabusys/__init__.py) を追加。公開サブパッケージ: data, strategy, execution, monitoring。パッケージバージョンを "0.1.0" に設定。
- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を起点に探索）。
  - 自動 .env ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサ実装: export 形式、クォート内エスケープ、インラインコメントの扱い、無効行スキップなどに対応。
  - 各種設定プロパティを公開: J-Quants / kabuStation / LINE / DB パス / Paper trading モード、監視閾値、環境種別（development/paper_trading/live）、ログレベル判定など。
  - 必須環境変数未設定時に明示的な ValueError を発生させる _require() を実装。
- AI ニュース / レジーム判定 (src/kabusys/ai)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを生成し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄別センチメント（ai_score）を算出する score_news(conn, target_date, api_key=None) を実装。
    - タイムウィンドウ計算（JST 前日15:00〜当日08:30 に対応）を calc_news_window で提供。
    - バッチ処理、チャンクサイズ制限、1銘柄当たりの記事／文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx で指数バックオフ）を実装。
    - レスポンス検証ロジックを実装（JSON 抽出、results リスト検査、コード整合性、スコア数値化、±1.0 クリップ）。
    - DuckDB への置換的書き込み（DELETE→INSERT）を行い、部分失敗時に他銘柄の既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api の patch を想定）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime(conn, target_date, api_key=None) を実装。
    - マクロニュース抽出、OpenAI でのセンチメント評価（JSON mode）、リトライ処理、スコア合成、DuckDB への冪等書き込みを含む完全なフローを実装。
    - API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。記事がない場合は LLM 呼び出しを行わない。
- Data プラットフォーム機能 (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルに基づく営業日判定ロジックを提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 未取得時は曜日ベースでフォールバック（週末＝非営業日）。最大探索日数で無限ループを防止。
    - 夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days=...) を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル、健全性チェック含む）を行う。
  - ETL パイプライン (src/kabusys/data/pipeline.py, etl.py)
    - ETL の結果を表すデータクラス ETLResult を公開（etl.py で再エクスポート）。
    - 差分取得、保存、品質チェックを組み合わせる ETL 設計に対応するためのユーティリティを実装（設計方針・定数含む）。
- Research（研究）機能 (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
      - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 乖離など。
      - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、平均売買代金、出来高比率。
      - calc_value(conn, target_date): PER / ROE（raw_financials と prices_daily の組合せ）。
    - DuckDB を用いた SQL ベース実装、データ不足時の None 返却、結果は (date, code) を含む dict のリストで返す。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）計算、ランク付けユーティリティ rank、ファクター統計サマリー factor_summary を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - 研究用ユーティリティは kabusys.data.stats の zscore_normalize を再利用（research パッケージの __init__ で公開）。
- 使いやすさ・テスト性
  - OpenAI 呼び出し箇所で明確な差し替えポイント（_call_openai_api）を用意し、ユニットテストでのモック化を容易に。
  - DuckDB のバージョン差異（executemany の空リスト問題）に配慮した実装を行い互換性を確保。
- ドキュメント相当のモジュール内コメント
  - 各モジュールに処理フロー、設計方針、注意点を詳細に記載。特にルックアヘッドバイアス回避（date.today()/datetime.today() を直接参照しない）、フェイルセーフポリシー、冪等性に関する注記を明記。

### Changed
- （初回リリースのため該当なし）

### Fixed
- フェイルセーフの挙動を明確化:
  - OpenAI API 呼び出し失敗やパース失敗時に、news_nlp と regime_detector の両方で例外を上位へ伝播させず「スコア 0.0（中立）」や「該当銘柄のスキップ」として継続するように実装。これにより ETL/スコアリングジョブの頑健性を向上。
- DuckDB への書き込みに関して、部分失敗時に他レコードを消さないよう DELETE→INSERT の順序で置換処理を実装。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- .env 自動ロード時に既存の OS 環境変数を保護する仕組み（protected set）を導入。override フラグと protected により重要な環境変数が意図せず上書きされることを防止。
- 必須トークン（OpenAI、J-Quants、KabuStation など）未設定時は明示的に ValueError を発生させることで安全な動作を促進。

---

注: 本 CHANGELOG はコードベースの内容から推測して作成しています。実際に公開する際はリリースノートや変更履歴に合わせて調整してください。