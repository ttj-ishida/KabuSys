CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載します。
このファイルは主にコードベースから推測した初期機能・設計決定をまとめたものです。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)
- 内部 (Internal)

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-03-29
------------------

Added
- 初期公開: KabuSys 日本株自動売買システムのコアモジュール群を追加。
  - パッケージエントリポイント: kabusys (version 0.1.0)
  - サブパッケージを公開: data, strategy, execution, monitoring（パッケージ構成を示すエクスポート）
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロード (.env, .env.local)。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境値のパース処理を実装（export プレフィックス、クォート、インラインコメント対応）。
  - 必須設定の取得ユーティリティ Settings を提供（J-Quants / kabu / Slack / DB パス / システムフラグなど）。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装。
- AI モジュール (kabusys.ai)
  - ニュースNLP (news_nlp)
    - raw_news と news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理(最大20銘柄)、記事数・文字数トリム、JSON モードのレスポンス検証を実装。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンス検証とスコアの ±1.0 クリッピング、DuckDB への冪等的書き込み（DELETE→INSERT）。
    - テスト容易性のため OpenAI 呼び出しの差し替えポイントを用意（モック可能）。
    - calc_news_window: JST ベースのニュース収集ウィンドウ算出ユーティリティを提供（ルックアヘッド防止）。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - titles を抽出する SQL、OpenAI 呼び出し、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI 呼び出しは news_nlp とは別実装にしてモジュール間結合を低減。
- リサーチモジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離の算出（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率の算出。
    - calc_value: raw_financials と当日の株価から PER / ROE を算出（EPS 無効時は None）。
    - DuckDB を用いた SQL 中心の実装。外部 API や発注ロジックにアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（既定: 1,5,21）で将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算するユーティリティ（欠損・有限性チェックあり）。
    - rank / factor_summary: ランク変換、基本統計量集約を実装。外部ライブラリ非依存。
  - research/__init__.py で主要関数群を再エクスポート。
- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を扱うユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB の有無に応じた曜日ベースのフォールバック、最大探索日数制限、バックフィル戦略、JPX カレンダー差分取得ジョブ（calendar_update_job）。
    - DuckDB の日付型互換処理、NULL ハンドリング、健全性チェックを実装。
  - ETL パイプライン:
    - pipeline モジュール: 差分取得／保存／品質チェックの枠組み（ETLResult データクラスを提供）。
    - ETLResult: 実行結果の構造化（取得数、保存数、品質問題、エラーメッセージ等）と to_dict()。
    - data.etl で ETLResult を再エクスポート。
  - jquants_client / quality など外部依存を想定した設計（保存関数の呼び出し・例外処理を想定）。
- DuckDB を一次データストアとして広範に採用（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等を前提）。

Security
- API キー / トークンは環境変数で管理（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- .env の自動ロード時に既存 OS 環境変数を保護する仕組みを実装（protected set を使用）。
- 短期的な安全策として KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

Fixed
- 初回リリースのため修正履歴はなし（コード内で多数のフォールバック・例外ハンドリングを実装済み）。

Changed
- 初回リリースのため変更履歴はなし。

Deprecated
- なし。

Removed
- なし。

Internal / Implementation notes
- ルックアヘッドバイアス対策:
  - datetime.today()/date.today() を直接参照せず、明示的に target_date を受け取る設計を優先。
  - prices_daily 等のクエリは target_date 未満 / <= 等の条件を厳密に扱う。
- OpenAI 連携:
  - モデル: gpt-4o-mini を想定。JSON Mode を利用して厳密な JSON 出力を期待。
  - レスポンスパース失敗や API エラーはフォールバックして処理継続（フェイルセーフ設計）。
  - テスト容易性のため _call_openai_api をモック可能にしている（ユニットテストでの差し替えを想定）。
- DuckDB 互換性:
  - executemany に空リストを渡すと不安定なバージョンがあるため、空チェックを行ってから実行する実装。
  - 日付型取り扱いの互換性を考慮して _to_date ユーティリティを導入。
- ロギングと診断:
  - 処理の主要ポイントで logger を用いた情報・警告・例外ログを記録。
  - JSON パース失敗、API 全リトライ消費、ROLLBACK 失敗時などのケースにおいて警告ログを出力。
- 設計方針・範囲:
  - 多くのモジュールは「読み込み／スコアリング／分析」に集中し、発注（execution）や運用（monitoring）側の実装は別モジュールとして分離する想定。
  - 外部発注や本番資金の操作はこのコードスナップショットの範囲外（設計上アクセスしない関数が多い）。

今後の予定（推測）
- strategy / execution / monitoring の具象実装（発注ロジック、リスク管理、実行モニタリング）の追加。
- CI/テスト向けのテストケース整備（OpenAI API モック、DuckDB テストデータ）。
- ドキュメント充実（Usage、Configuration、ETL 手順、研究ノート等）。

注記
- 本 CHANGELOG は与えられたソースコードからの推測に基づいて作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴・リリース定義をご参照ください。