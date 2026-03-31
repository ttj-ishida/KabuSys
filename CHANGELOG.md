CHANGELOG
=========

このCHANGELOGは「Keep a Changelog」形式に準拠しています。  
コード内容から推測して記載しています。実際のリリースノートと差異がある可能性があります。

Unreleased
----------

（なし）

0.1.0 - 2026-03-31
------------------

Added
- 初回リリースとして kabusys パッケージを追加。
  - パッケージ公開情報
    - バージョン: 0.1.0
    - パッケージ説明: 日本株自動売買システムのコアライブラリ（モジュール分割: data, research, ai, monitoring, strategy, execution 等を想定）。
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env パーサー実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ文字等対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護（既存OS環境変数を protected として扱い上書きを制御）。
  - Settings クラスを提供し、必要な設定値をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト付き）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパス）
    - PID_FILE_PATH, CPU/MEMORY/DISK 閾値（監視用）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev ユーティリティプロパティ
- AI（自然言語処理・レジーム判定）（kabusys.ai）
  - news_nlp モジュール（score_news）
    - ニュース記事を銘柄単位に集約し、OpenAI (gpt-4o-mini) の JSON Mode を用いてセンチメントを算出。
    - タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30 相当）の計算（UTC naive datetime を使用）。
    - バッチ処理（最大20銘柄／チャンク）、記事数・文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - リトライ/バックオフ（429, ネットワーク断, タイムアウト, 5xx）実装。
    - レスポンス検証（JSON 抽出、results リスト、code/score の妥当性検査）、スコアを ±1.0 にクリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT をチャンク単位で実行）およびトランザクション制御。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。
  - regime_detector モジュール（score_regime）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と
      マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロ記事の抽出（マクロキーワードによるフィルタ、最大 _MAX_MACRO_ARTICLES 件）。
    - OpenAI 呼び出し（_MODEL: gpt-4o-mini）とリトライ/バックオフ、JSON パースとフォールバック（失敗時 macro_sentiment=0.0）。
    - レジームスコアの合成としきい値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため OpenAI 呼び出し箇所を置換可能に設計。
- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar テーブルを用いた営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合や該当日が未登録の場合は曜日ベース（週末除外）でフォールバック。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - calendar_update_job を実装し J-Quants API から差分取得（バックフィル、健全性チェック、保存は jquants_client を経由して冪等に保存）。
  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを導入（取得数／保存数／品質チェック結果／エラーを集約）。
    - 差分更新、バックフィル方針、品質チェックの設計方針を実装の指針として準備（jquants_client, quality モジュールとの連携を想定）。
    - DuckDB を前提としたテーブル存在チェック等のユーティリティ。
- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum（1M/3M/6M リターン・200 日 MA 乖離）、calc_volatility（20 日 ATR, 相対 ATR, 平均売買代金, 出来高変化率）、calc_value（PER/ROE）を実装。
    - DuckDB の SQL ウィンドウ関数を利用し、データ不足時は None を返す等の堅牢性を確保。
    - 全処理は prices_daily / raw_financials のみ参照し外部発注等には接触しない設計。
  - feature_exploration
    - calc_forward_returns（複数ホライズンの将来リターンを一度のクエリで取得）、calc_ic（スピアマンランク相関による IC 計算）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で完結。
  - research.__init__ で主要関数を再エクスポート（便利な公開 API）。
- パッケージ公開
  - kabusys.__init__ に __version__ = "0.1.0" と __all__ の設定。

Fixed / Robustness
- 多くの箇所で「ルックアヘッドバイアス防止」を明示し、target_date 未満のデータのみ参照する実装に統一。
- OpenAI API 呼び出しに対して堅牢なリトライとログ出力を実装。API エラーや JSON パースエラー時は例外を投げずフォールバックする設計（サービス可用性重視）。
- DuckDB への書き込みはトランザクションで保護し、失敗時は ROLLBACK を試行して例外を上位へ伝播。
- .env パーサーの強化により、引用符内のエスケープやインラインコメントを正しく処理。

Changed
- 初回リリースのため「変更」は特になし。

Removed
- 初回リリースのため「削除」は特になし。

Security
- セキュリティ関連: API キー（OpenAI 等）やトークンは環境変数経由で取得し、Settings にて必須チェック（未設定時は ValueError）を行うことで誤動作を抑止。

Notes / Requirements
- 主な依存: duckdb, openai SDK（コード内で import を確認）。
- 実行には環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）や DuckDB のテーブル（prices_daily, raw_news, market_regime, ai_scores, raw_financials, market_calendar 等）が必要。
- 実運用前に jquants_client / quality / monitoring 等、外部モジュール実装とデータスキーマ整備が必要。

今後の作業候補（コードから推測）
- jquants_client と quality モジュールの実実装および統合テストの追加。
- 単体テスト・統合テストでの OpenAI 呼び出しモックの充実（既に差し替え可能な設計）。
- ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づくサンプル ETL/バッチの公開。