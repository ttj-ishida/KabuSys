# CHANGELOG

すべての注目すべき変更点を記録します。  
このプロジェクトでは Keep a Changelog 準拠の形式を採用しています。

リリース日はパッケージの初期公開日として記載しています。

## [Unreleased]

- （今後の変更をここに記載）

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期実装を追加
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - モジュール公開: data, strategy, execution, monitoring をパッケージの __all__ として公開（src/kabusys/__init__.py）。

- 環境変数・設定管理コンポーネントを追加（src/kabusys/config.py）
  - .env / .env.local ファイルを自動で検出・読み込み（プロジェクトルート検出は .git または pyproject.toml を起点）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサは export 形式、クォート付き値（バックスラッシュエスケープ対応）、インラインコメント処理などの堅牢なパースをサポート。
  - override / protected オプションを使った上書き制御（OS 環境変数保護）を実装。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等をプロパティで取得。値検証（有効な env・log level の検査）とヘルパー（is_live 等）を実装。
  - 必須環境変数未設定時は明示的なエラーメッセージを送出。

- ニュース NLP（AI）機能を追加（src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py）
  - raw_news / news_symbols テーブルから銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へ JSON mode でバッチ評価して銘柄別センチメント（ai_scores テーブル）を書き込む。
  - 処理ウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を採用。トリムや最大記事数などトークン肥大化対策を実装。
  - バッチサイズ、最大記事数、最大文字数等を定数化。
  - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。非再試行エラーはスキップして継続（フェイルセーフ設計）。
  - レスポンスバリデーション: JSON の復元（前後余分テキストが混入した場合の最外 {} 抽出）、results キーと要素検証、スコアの数値化と ±1.0 クリップ。
  - DuckDB の executemany の制約を考慮し、空パラメータのケースをチェックしてから実行。部分失敗時に既存スコアを保護するため、DELETE→INSERT をコード単位で行う。
  - テスト容易性のため _call_openai_api を patch 可能に設計。

- 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を計算。
  - OpenAI 呼び出しは個別実装（news_nlp と共有しない）で、Retry/Backoff/5xx ハンドリングを実装。API 失敗時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
  - DuckDB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
  - ルックアヘッドバイアスを防ぐため、target_date 未満のデータのみ使用し、datetime.today() へ依存しない実装。

- リサーチ（ファクター計算・特徴量探索）モジュールを追加（src/kabusys/research/*）
  - factor_research.py:
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）を DuckDB 上で計算。
    - データ不足時の None ハンドリング、営業日ベースのホライズン取扱い、SQL ウィンドウ関数利用。
  - feature_exploration.py:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を1クエリで取得。
    - IC（Spearman の ρ）計算、ランク付けユーティリティ（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージの __init__ で主要関数を再エクスポート。

- データプラットフォーム関連モジュールを追加（src/kabusys/data/*）
  - calendar_management.py:
    - market_calendar の管理、JPX カレンダー取得ジョブ（calendar_update_job）、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 存在時は DB 値優先、未登録日は曜日ベースでフォールバックする一貫性あるロジック。
    - 最大探索日数やバックフィル、健全性チェック（未来日付の異常判定）を実装。
  - pipeline.py / etl.py:
    - ETL パイプライン設計に基づくユーティリティ（差分取得、保存、品質チェック）を実装。
    - ETLResult dataclass を提供（取得件数・保存件数・品質問題・エラーの集約、has_errors/has_quality_errors、辞書変換メソッド）。
    - DuckDB テーブル存在チェック、最大日付取得等のユーティリティを実装。
  - data パッケージは jquants_client, quality など外部サブモジュールと連携する設計（関数呼び出し箇所を用意）。

- その他ユーティリティ
  - 設計方針として「ルックアヘッドバイアス防止」を徹底（関数は datetime.today()/date.today() に全般的に依存せず、target_date を明示的に受け取る）。
  - DuckDB との互換性を意識した実装（executemany の空リスト回避、日付型取り扱いユーティリティ _to_date など）。
  - ロギング出力を適切に配置し、失敗やフォールバック時に情報を残す。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- .env ロード時に OS 環境変数を保護する protected 機能を実装（.env.local の override を使っても重要な OS 環境変数は上書きされない設計）。

---

注）本 CHANGELOG はソースコードから実装意図・API・挙動を推測して作成しています。実際のリリースノート作成時には開発チームによる確認・補足（バグ修正履歴、互換性注意点、既知の問題など）を反映してください。