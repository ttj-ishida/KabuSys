CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、SemVer を想定しています。

## [Unreleased]

※ 現在のコードはリリース v0.1.0 相当の初期機能群を含みます。今後の変更はこのセクションに記載されます。

---

## [0.1.0] - 2026-04-04

初回公開リリース。日本株自動売買システムの骨格となる以下の主要コンポーネントを実装しました。実用的な ETL / データ基盤、リサーチ用のファクター計算、ニュース NLP と市場レジーム判定、環境設定管理などを含みます。

### Added
- パッケージ基礎
  - kabusys パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - package の公開モジュール一覧を __all__ で定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーの高機能化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメント扱いのルール（クォートの有無で挙動を制御）
  - _require による必須環境変数チェック（未設定時は ValueError を送出）。
  - 各種プロパティ:
    - J-Quants / kabu API / LINE API の設定取得（既定値や空文字扱いの方針を含む）
    - データベースの既定パス（DUCKDB_PATH, SQLITE_PATH）
    - 監視用ファイルパスと閾値（PID ファイル、kill flag、CPU/Memory/Disk の閾値）
    - 実行環境判定（development / paper_trading / live）と LOG_LEVEL バリデーション
    - is_live / is_paper / is_dev ヘルパー

- AI（ニュース NLP・レジーム判定） (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へ送信してセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を正確に扱う calc_news_window 実装。
    - バッチ処理（1 API コール当たり最大 20 銘柄）、1 銘柄あたりの最大記事数・最大文字数制限（トリム）。
    - JSON Mode レスポンスのバリデーションと復元処理（前後の余計なテキストが混ざった場合に {} を抽出して復元）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ。失敗時は個別チャンクをスキップして継続（フェイルセーフ）。
    - DuckDB の executemany の空リスト制約を考慮した書き込みロジック（DELETE → INSERT、部分失敗への配慮）。
    - テスト容易性: _call_openai_api 関数はユニットテスト時にパッチ可能。
    - OpenAI API キー未設定時は ValueError を送出。

  - regime_detector.score_regime
    - ETF 1321（日経225連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースは news_nlp.calc_news_window と同様のウィンドウで抽出し、OpenAI に JSON 出力を要求して macro_sentiment を取得。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 へフォールバック（例外を波及させない）。
    - レジーム判定値の合成・クリップ処理と閾値に基づくラベル化を実装。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行し、エラー時には ROLLBACK を試みる。

- データ基盤 (kabusys.data)
  - calendar_management
    - JPX カレンダー（market_calendar）を参照する営業日判定ユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得時の曜日ベースのフォールバック実装（週末を非営業日扱い）。
    - next/prev の探索は最大探索日数制限を設け、無限ループを防止。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に保存する夜間バッチ処理（バックフィル、健全性チェックあり）。
  - pipeline / etl
    - ETLResult データクラスの実装（ETL 実行結果のサマリ + 品質問題・エラー収集）。
    - pipeline モジュール型（ETLResult）を公開。
    - ETL の設計方針をコードに反映（差分更新、バックフィル、品質チェックの継続動作、id_token 注入可能性等）。
  - jquants_client との連携点を用意（fetch/save 系関数を想定して呼び出し）。

- リサーチ / ファクター (kabusys.research)
  - factor_research
    - calc_momentum: 1m/3m/6m リターン、200 日 MA 乖離の算出。データ不足時に None を返す仕様。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等の計算。
    - calc_value: raw_financials から最新財務データを取得して PER・ROE を算出（EPS が 0 または欠損時は None）。PBR・配当利回りは未実装。
    - DuckDB のウィンドウ関数を活用する実装。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する SQL 実装。horizons の検証あり。
    - calc_ic: Spearman（ランク）相関で IC を計算。データが不足（有効レコード < 3）なら None を返す。
    - rank: 同順位は平均ランク扱い（丸めで ties の検出漏れを防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算。
    - 重要: これらリサーチ関数は外部 API を呼ばず、prices_daily / raw_financials のみ参照する設計（本番口座や発注 API にアクセスしない）。

### Changed
- （初版のため「Added」のみ。将来のリリースで差分を記載します）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーは明示的に提供するか環境変数 OPENAI_API_KEY を設定する必要あり。未設定時は該当関数で ValueError を発生させる仕様により誤操作を防止。

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策:
  - 全ての「日付ベース」処理は datetime.today()/date.today() を直接参照せず、明示的に target_date を受け取る設計。
  - DB クエリは target_date 未満 / 以前等の条件で未来データの参照を防止。
- フェイルセーフ:
  - LLM/API 失敗時はスコアを 0 または該当チャンクをスキップして処理継続。致命的に停止しない方針。
- テスト性:
  - OpenAI 呼び出しラッパー（_call_openai_api）を patch できるようにしてユニットテストを容易にしている。
  - 環境自動ロードは環境変数で無効化可能（テスト時に .env の自動読み込みを抑止）。
- DuckDB 互換性に配慮:
  - executemany に空リストを渡せないバージョンへの対処を行っている（事前チェック）。
- 未実装 / 既知の制約:
  - calc_value における PBR / 配当利回りは未実装。
  - jquants_client の具体的実装（fetch/save 系）は外部モジュールとして想定。実際の API 呼び出し部分は依存する。
  - OpenAI SDK やモデル仕様（gpt-4o-mini の JSON Mode 等）は将来の SDK 変更で影響を受ける可能性あり。

---

開発・運用に際しての備考やバグ報告・機能要望は Issue を立ててください。今後のリリースでは API 安定化、監視・発注実装、追加ファクターや品質チェックの強化を予定しています。