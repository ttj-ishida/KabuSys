# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお本リポジトリの現時点のバージョンは 0.1.0（src/kabusys/__init__.py）です。

## [Unreleased]
- 特になし（初回リリース: 0.1.0 を参照）

---

## [0.1.0] - 2026-04-09

初期公開リリース。日本株自動売買・リサーチ用ライブラリの骨組みと主要機能を実装。

### Added
- パッケージ基礎
  - パッケージメタ情報と公開モジュール指定を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env/.env.local の読み込み順序と上書きルール（OS 環境変数保護）。
  - .env パースの堅牢化:
    - export プレフィックス対応、コメント処理、シングル/ダブルクォート内のエスケープ対応。
    - 無効行のスキップ処理。
  - 各種設定プロパティを実装（J-Quants トークン、kabu API 設定、LINE API、データベースパス、Paper Trading 設定、監視閾値、環境・ログレベル検証等）。
  - PAPER_FILL_MODE 等の値検証（許容値チェック）とエラーメッセージ。

- AI（自然言語処理）機能（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode で銘柄ごとのセンチメントを算出し ai_scores テーブルへ保存する score_news を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST → UTC変換）の calc_news_window 実装。
    - バッチ送信（最大 20 銘柄 / バッチ）、1銘柄あたり記事数・文字数上限（トークン肥大対策）。
    - API エラー（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフリトライ。
    - レスポンスのバリデーションと厳格な JSON 抽出、スコアの ±1.0 クリッピング。
    - 部分成功を考慮した DB の置換戦略（該当 code の DELETE → INSERT、DuckDB executemany の注意）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ冪等書き込みする score_regime を実装。
    - LLM 呼び出しは独立実装でモジュール間結合を避ける設計。
    - API リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）、レスポンスパースのフォールバック。
    - ルックアヘッドバイアス対策（date 引数ベース、DB クエリは target_date 未満のみ使用）。

- データ関連（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー取り扱いロジックの実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar の有無に応じた DB 優先・未登録日は曜日ベースでフォールバックする一貫した振る舞い。
    - calendar_update_job による J-Quants からの差分取得と保存処理（バックフィル、健全性チェック、ON CONFLICT 相当の冪等保存のため jquants_client 呼び出し）。
    - 最大探索日数や見通し日数等の保護パラメータを定義し無限ループや極端なデータを防止。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（ETL 実行結果の構造化、品質問題・エラーの収集、to_dict によるシリアライズ）。
    - 差分更新・バックフィル方針、品質チェックの扱いについて仕様コメントを追加。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
  - jquants_client（参照）との統合ポイントを想定した設計（fetch/save 関数を利用）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py: モメンタム・ボラティリティ・バリュー系ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（データ不足時の None 処理）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（NULL 伝播制御、必要行数条件）。
    - calc_value: raw_financials から直近財務を取得して PER / ROE を計算。
    - DuckDB を利用した SQL + Python 実装で外部 API へはアクセスしない設計。
  - feature_exploration.py: 将来リターン・IC（Spearman）・統計サマリー等を実装。
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21）について LEAD を使用して将来リターンを一度に算出。
    - calc_ic: factor_records と forward_records を code で突合し Spearman ρ（ランク相関）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを付与するランク関数（round(v,12) による丸めを行い ties の判定安定化）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
  - research パッケージの __init__ で主要関数をエクスポート。

### Changed
- （新規リリースのため変更履歴なし）

### Fixed
- （新規リリースのため修正履歴なし）

### Security
- （該当なし）

---

注記（設計上のポイント）
- ルックアヘッドバイアス対策のため、全ての「日次」処理は内部で datetime.today()/date.today() に依存しないよう設計されています（target_date を明示的に受け取る）。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスを厳密にバリデートします。API 失敗時は例外で停止せずフェイルセーフ（スコア=0 あるいは該当銘柄をスキップ）で継続する設計です。
- DuckDB のバージョン差異に配慮した実装（executemany 空リストの扱い回避、date 型ハンドリングなど）を行っています。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト容易性）。

もし CHANGELOG に追加したい詳細（例: リリース日変更、リリースノートの粒度、既知の制限や将来予定）があれば指示してください。