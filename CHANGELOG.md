# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成しています。

フォーマット:
- Unreleased — 今後の変更（空の場合は変更なし）
- 各リリースは日付付きで記載

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」の基礎機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化情報を追加（kabusys.__init__、__version__ = "0.1.0"）。
  - パッケージ公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定 / 環境変数管理
  - .env / .env.local からの自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルート検出は .git または pyproject.toml を探索（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env の行パーサは export プレフィックス、引用符（シングル/ダブル）のエスケープ、行内コメント処理に対応。
    - 読み込み時に既存 OS 環境変数を保護するため protected キーセットを利用。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能（J-Quants / kabu API / Slack / DB パス / 監視閾値 等）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）を実装。
    - 必須値未設定時は明確な ValueError を送出。

- AI（自然言語処理）モジュール
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news + news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON モードへバッチ送信してセンチメントを算出。
    - チャンク処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄当たり記事数・文字数上限を実装（トリム処理）。
    - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンスバリデーション（JSON 抽出、results 配列・code/score の検証、未知コードの無視、スコアの ±1.0 クリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗で他コードを保護）。
    - テスト容易性: OpenAI 呼び出し箇所をモック可能（内部 _call_openai_api の差し替え）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を実装（calc_news_window）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタして LLM に渡す。
    - OpenAI 呼び出しは最大リトライ、API 異常時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - 結果を market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT、例外時は ROLLBACK）。
    - LLM クライアント注入とテスト用差し替えを想定。

- データプラットフォーム（Data）モジュール
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装（J-Quants API 経由で差分取得・冪等保存）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した実装。
    - 最大探索期間 (_MAX_SEARCH_DAYS) による無限ループ防止、バックフィルや健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult dataclass による実行結果集約（取得数、保存数、品質問題、エラーなど）。
    - 差分更新、バックフィル日数制御、品質チェックフック（quality モジュールを想定）に対応。
    - DuckDB を前提としたテーブル存在/最大日付チェックユーティリティを提供。
    - jquants_client との連携を想定した設計（fetch/save 関数を呼び出す形）。
  - ETL 公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。

- リサーチ（研究）モジュール
  - factor_research: ファクター計算を実装（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER/ROE）等を DuckDB SQL で算出。
    - データ不足時は None を返す等、安全な処理。
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、rank 関数、統計サマリーなどを実装（kabusys.research.feature_exploration）。
    - calc_forward_returns は複数ホライズンをサポートし、入力検証（horizons の範囲）を行う。
    - calc_ic はコードで結合し、3 レコード未満で None を返す堅牢な実装。
    - factor_summary は count/mean/std/min/max/median を計算。
  - research パッケージの __init__ で便利関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 共通実装上の注意点（横断的）
  - DuckDB を主要な永続層として利用。SQL と Python の組み合わせで計算処理を実行。
  - すべての「日付基準」関数は datetime.today()/date.today() を直接参照しない方針（ルックアヘッドバイアス防止）。target_date を明示的に受け取る設計。
  - OpenAI 呼び出しに対してリトライ/バックオフ/レスポンス検証を行い、API 異常時はスキップまたは安全側の既定値を用いる（例: macro_sentiment=0.0）。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 想定）し、例外発生時は ROLLBACK を試みる実装。
  - DuckDB の executemany における空リスト扱いに関する互換性考慮（空時は呼ばない）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 既知の制約 / 注意点 (Notes)
- OpenAI API キーは関数引数で注入可能だが、未指定時は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出する。
- news_nlp と regime_detector はいずれも gpt-4o-mini を想定した JSON モードでの利用を前提としている（API サービス側の変更により調整が必要になる可能性あり）。
- DuckDB のバージョン差異により list 型バインド等で挙動差があるため、executemany を用いた互換性確保を行っている。
- calendar_update_job や ETL は外部 API（J-Quants）に依存するため、実行環境での API クレデンシャル/ネットワーク設定が必要。

---

今後のリリースに向けて、
- strategy / execution / monitoring の具体的な実装（取引ロジック・発注・プロセス監視）や、
- テスト補助、CI/CD、ドキュメント整備（API 仕様、DB スキーマの明記）、
- エラーメトリクスやリトライの細かなチューニング、
などが想定されます。必要であれば CHANGELOG の項目を拡張して詳細に反映します。