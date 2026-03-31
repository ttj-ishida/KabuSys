Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトの変更履歴は "Keep a Changelog" の慣例に従っています。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 各リリースに対して Added / Changed / Fixed / Deprecated / Removed / Security の分類を付与しています。

Unreleased
----------

- 既知の未解決点 / 注意点
  - data/pipeline.py の末尾に未完成（truncated）と思われる実装箇所が存在します（"return date.fro" のような不完全な行）。リリース前に該当ヘルパー関数の完成とテストが必要です。
  - README や運用手順（環境変数記載など）がまだ整備されていない可能性があります。環境変数必須項目のドキュメント化を推奨します。

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ基盤
  - 初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開用 __all__ に主要サブパッケージを定義（data, strategy, execution, monitoring）。

- 環境設定 / config
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env パーサーの実装（export 形式やクォート、コメントの取り扱い、エスケープ対応を含む）。
  - OS 環境変数を保護する protected オプション、.env.local による上書き挙動のサポート。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ。
  - Settings クラスで以下の設定プロパティを提供・検証:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
    - CPU / Memory / Disk アラート閾値（デフォルト値あり）
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev の便宜プロパティ

- AI（自然言語処理）機能
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を用いたニュースセンチメントスコアリング機能（score_news）。
    - ニュース対象ウィンドウ計算（JST ベース → DB 比較は UTC naive datetime）。
    - 銘柄単位で記事を集約（記事数・文字数のトリム）、最大バッチサイズで OpenAI にバッチ送信。
    - OpenAI 呼び出しは gpt-4o-mini + JSON Mode を利用、429/ネットワーク/タイムアウト/5xx に対する指数バックオフ付きリトライ。
    - レスポンスの堅牢なバリデーション (_validate_and_extract)、JSON パース回復ロジック、スコアの ±1.0 クリップ。
    - DuckDB への idempotent な書込み（DELETE → INSERT、部分失敗時に他銘柄のスコアを保護）。
    - テストのために _call_openai_api をモック差し替え可能に設計。
  - kabusys.ai.regime_detector:
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定（score_regime）。
    - ma200 比率計算（target_date 未満のデータのみ使用してルックアヘッドバイアスを防止）。
    - マクロニュース抽出（キーワードフィルタ）、LLM によるセンチメント評価（gpt-4o-mini, JSON Mode）、API エラー時はフォールバック macro_sentiment=0.0。
    - レジームスコア合成および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、エラー時は ROLLBACK を試行）。
    - API 再試行ロジックとエラーハンドリング（RateLimit / Connection / Timeout / 5xx / JSON parse 等を考慮）。

- リサーチ（ファクター・特徴量分析）
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）等の計算関数（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を活用して高速に集計。データ不足時の None 処理など堅牢設計。
    - 結果は (date, code) ベースの dict リストで返却。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意の horizon 対応、入力検証あり）。
    - IC（Information Coefficient）計算（Spearman の ρ ベース、rank 処理で同順位の平均ランクを採用）。
    - factor_summary（count/mean/std/min/max/median 計算）、rank ユーティリティなど、外部ライブラリに依存しない実装。

- データプラットフォーム / Data
  - kabusys.data.calendar_management:
    - JPX カレンダー管理ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar がない場合の曜日ベースフォールバック、DB 登録優先の一貫した振る舞い。
    - 夜間バッチ job（calendar_update_job）で J-Quants API から差分取得→保存（バックフィル / サニティチェックを含む）。
  - kabusys.data.pipeline:
    - ETL パイプラインの骨格（差分取得、保存、品質チェックの流れ）を定義。
    - ETLResult dataclass を導入（取得/保存数、品質問題、エラー一覧、has_errors / has_quality_errors / to_dict を提供）。
  - kabusys.data.etl:
    - pipeline.ETLResult を再エクスポート（public API）。

Changed
- 初期リリースのため特記なし。

Fixed
- 初期リリースのため特記なし。

Deprecated
- 初期リリースのため特記なし。

Removed
- 初期リリースのため特記なし。

Security
- セキュリティに関する特記事項なし。  
  - ただし OpenAI API キー等の機密情報は Settings 経由で環境変数から取得する設計のため、運用時は環境変数管理に注意してください。

Notes / 実装上の設計意図（概要）
- ルックアヘッドバイアス対策:
  - AI/リサーチ関数は内部で datetime.today()/date.today() を参照せず、必ず caller が target_date を与える形にしている（研究・バックテストでのバイアス防止）。
- DuckDB を主要な分析/保存用ローカル DB として採用。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密な検証（JSON パース、構造検査、数値型検証）を行う。
- API 呼び出しに対するリトライ／バックオフとフェイルセーフ（失敗時はスコアを 0 にフォールバック、処理は継続）を重視。
- DB 書き込みは冪等性を意識（DELETE → INSERT、部分書込みで既存データ保護）。
- テスト容易性: OpenAI 呼び出し箇所はモック差し替え可能に設計。

開発者向け TODO / 今後の改良提案
- data/pipeline.py の未完成箇所を修正してユニットテストを追加する（現在のコード断片は構文エラー/実行時エラーになる可能性あり）。
- ドキュメント化: 必須環境変数一覧（.env.example）、運用手順（デプロイ時の env 管理、ワーカ起動、監視閾値の調整）を整備する。
- strategy / execution / monitoring パッケージの具体実装が未確認のため、実装状況に応じて CHANGELOG を更新する。
- セキュリティ: 機密情報管理（Vault 等）の導入検討。

以上。