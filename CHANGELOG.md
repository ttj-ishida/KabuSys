# Changelog

すべての重要な変更は「Keep a Changelog」形式に従って記載しています。日付はリポジトリのコード内容（__version__ = "0.1.0"）および現状の実装から推測して付与しています。

全般的な方針
- ルックアヘッドバイアス回避のため、datetime.today() / date.today() を業務ロジック内部で直接参照しない実装になっています（関数に target_date を渡す形）。
- OpenAI 呼び出しは JSON mode（厳密な JSON 出力）を想定し、API エラーやパース失敗時はフェイルセーフ（スコア 0.0、スキップ）で継続する設計です。
- DuckDB をデータストアとして利用する想定で、互換性（例: executemany の空リスト問題）に配慮した実装になっています。
- 外部依存を最小化（pandas 等不使用）し、テストしやすく API 呼び出し箇所を差し替え可能（patch）にしています。

Unreleased
- 今後の改善候補（コードから推測）
  - PBR / 配当利回りなどのバリュー指標の追加
  - ai モジュールのレスポンス検証強化・メトリクス収集
  - ETL の並列化・性能改善
  - より詳細なスキーマ検証ツールの導入
  - J-Quants / kabu API 呼び出しのリトライ/バックオフ共通化

[0.1.0] - 2026-04-01
Added
- 基本パッケージ初期実装
  - パッケージメタデータ: kabusys.__version__ = "0.1.0"
  - 公開モジュール群: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 読み込み優先順位: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env のパース実装（export プレフィックス、クォート、エスケープ、コメント処理に対応）。
  - 環境変数必須チェック (_require) と Settings クラスを提供。
  - Settings で参照する主要な環境変数（必須・デフォルト値を含む）を実装:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意/デフォルト: KABU_API_BASE_URL (default http://localhost:18080/kabusapi), DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK 閾値, KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL
  - KABUSYS_ENV/LOG_LEVEL のバリデーション。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news: raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数・文字数上限、JSON mode 期待、リトライ（429/ネットワーク/5xx）機構。
    - レスポンスのバリデーションと ±1.0 クリップ。
    - DuckDB の executemany 空リスト制約に対する対策（空チェック）。
    - calc_news_window: JST のニュースウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC Naive datetime に変換するユーティリティ。

  - regime_detector.score_regime: ETF 1321（日経225連動ETF）の 200 日 MA 乖離（重み 70%）とニュース LLM マクロセンチメント（重み 30%）を合成して market_regime テーブルへ冪等的に書き込み。
    - ma200 計算（target_date 未満のデータのみ使用でルックアヘッド回避）、記事のフィルタ（マクロキーワード）、OpenAI 呼び出し（個別実装）、リトライ/バックオフ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - スコア合成とラベル付与（bull / neutral / bear）。
    - BEGIN / DELETE / INSERT / COMMIT の冪等的 DB 書き込み。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX 市場カレンダー同期ジョブ（calendar_update_job）: J-Quants から差分取得、バックフィル、健全性チェック、冪等保存。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB に calendar データがない場合は曜日ベース（平日）でフォールバック。DB 登録ありの場合は DB 値優先。
    - 最大探索日数制限、NULL 値に対する警告ログ等の堅牢化。

  - pipeline / ETL:
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - ETLResult に品質チェック問題（quality.QualityIssue のリスト）や errors を保持するフィールドを持ち、to_dict による辞書化を提供。
    - 差分フェッチ、バックフィル、品質チェックを想定した構造。外部 jquants_client と quality モジュールへの委譲を想定。

  - jquants_client 経由での保存処理（save_*）を使う想定で、DB への冪等保存方針が明示されている。

- 研究用モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials から最新の EPS/ROE を取得し PER/ROE を計算（EPS が 0/欠損なら None）。PBR/配当は未実装。
    - DuckDB のウィンドウ関数を活用した実装。

  - feature_exploration:
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証（1..252）。
    - calc_ic: スピアマンランク相関（IC）の計算。十分なサンプルが無い場合は None。
    - rank, factor_summary: ランク変換（同順位は平均ランク）と統計サマリ（count/mean/std/min/max/median）。

- テスト容易性 / 実装上の配慮
  - OpenAI 呼び出し部分は内部で _call_openai_api を経由しており、unittest.mock.patch で差し替え可能。
  - API キー（OPENAI_API_KEY）は関数引数経由で注入でき、テスト時に外部環境変数に依存しないよう設計。
  - DuckDB のデータ型や日付戻り値を扱うユーティリティ（_to_date）を用意。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- 環境変数の取り扱いに注意: 自動ロードで OS 環境を上書きしない保護ロジックを実装（protected set）。
- OpenAI API キーや各種トークンは必須項目として Settings で参照するため、シークレット管理を適切に行う必要があります。

注意事項 / 既知の制約（コードから推測）
- OpenAI モデル: デフォルトで gpt-4o-mini（JSON mode）を使用するため、API の利用料金・レート制限に注意が必要。
- ニュース・レジーム系処理は LLM のレスポンスに依存するため、外部 API の不安定さを考慮して運用すること（フェイルセーフはあるが結果が欠落する可能性あり）。
- DuckDB スキーマ（期待されるテーブル）
  - prices_daily, raw_news, ai_scores, market_regime, market_calendar, news_symbols, raw_financials などが想定されている。これらのスキーマ・列名が実装と一致することを事前に確認してください。
- 一部処理は DuckDB のバージョン差異へ配慮した実装（executemany の空リスト回避など）を行っていますが、運用環境の DuckDB バージョン依存性に注意してください。
- calc_news_window 等は UTC naive datetime を返す実装のため、DB の日時保存が UTC 前提であることを確認してください。

導入 / 移行メモ（初回セットアップ時の推奨手順）
1. 必須環境変数を設定:
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
2. .env / .env.local をプロジェクトルートに配置する場合は .gitignore を設定し、安全に管理すること。
3. DuckDB ファイル（デフォルト data/kabusys.duckdb）と必要テーブルを準備（スキーマはドキュメント参照）。
4. ログレベル・KABUSYS_ENV を環境に応じて設定（development / paper_trading / live）。
5. テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。

---

この CHANGELOG は、リポジトリ内のコードと docstring から推測して作成しています。リリース日やカテゴリの振り分けは実際のリリース方針に合わせて調整してください。必要であれば、実際のコミット履歴やタスク管理（Issue/PR）に基づくより詳細な CHANGELOG の生成も対応します。