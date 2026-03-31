CHANGELOG
=========

すべての重要な変更をこのファイルに記載します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- バージョンはセマンティックバージョニングに従います。
- セクション: Added / Changed / Fixed / Removed / Security

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - src/kabusys/__init__.py
    - パッケージメタ情報を追加: __version__ = "0.1.0"
    - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に設定

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを実装
      - 自動読み込み順序: OS環境変数 > .env.local > .env
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
      - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）
      - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応
      - .env の読み込みで OS 環境変数（protected）を保護する仕組みを実装（override フラグと protected 集合）
    - Settings クラスを提供（settings = Settings()）
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須検査
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値
      - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL 検証ユーティリティ
      - is_live / is_paper / is_dev の短絡プロパティ

- AI（NLP・レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む機能を実装
    - 主な仕様:
      - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC に変換して DB 比較）
      - 1銘柄あたり最新 _MAX_ARTICLES_PER_STOCK (デフォルト10) 件、最大文字数トリム（_MAX_CHARS_PER_STOCK）
      - バッチ処理: 最大 _BATCH_SIZE (デフォルト20) 銘柄／リクエスト
      - レート制限(429)、ネットワーク断、タイムアウト、5xx サーバーエラーに対する指数バックオフリトライ
      - レスポンスの厳密な JSON 検証（results リスト、code と score 検査）、スコアを ±1.0 にクリップ
      - ETL と同様に DuckDB への冪等的書き込み（DELETE → INSERT。部分失敗時に他銘柄データを保護）
      - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api を patch 可能）
      - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計
  - src/kabusys/ai/regime_detector.py
    - 日次の市場レジーム判定機能を実装（score_regime）
    - 主な仕様:
      - 対象 ETF: 1321（日経225連動型）を使用して 200 日移動平均乖離を計算（_MA_WINDOW=200）
      - マクロ経済ニュースセンチメント（news_nlp の calc_news_window を利用して記事を抽出）と組み合わせる
      - 合成ルール: ma 成分 70% / macro 成分 30%、スケール・クリップにより最終スコアを -1.0〜1.0 に正規化
      - レジームラベル閾値: bull / neutral / bear（閾値 0.2）
      - OpenAI 呼び出しは再試行・フォールバック実装、API 失敗時は macro_sentiment=0.0 として継続
      - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時には ROLLBACK）

- Data / ETL / カレンダー
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等を実装
    - 特長:
      - market_calendar テーブルが未取得の場合は曜日ベース（週末除外）にフォールバック
      - DB 登録があれば DB 値優先、未登録日は曜日フォールバックで一貫処理
      - 最大探索日数に上限を設け無限ループを防止（_MAX_SEARCH_DAYS）
      - calendar_update_job: J-Quants API から差分取得→保存（バックフィル／健全性チェック組込）
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプライン用ユーティリティを実装
    - ETLResult dataclass を定義（取得数・保存数・品質チェック結果・エラー一覧等を保持）
    - 差分取得ロジック、テーブル存在チェック、最大日付取得ユーティリティ等を実装
    - idempotent な保存（jquants_client の save_* を前提）・品質チェックフローを想定
    - etl モジュールは pipeline.ETLResult を再エクスポート

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー関連のファクター計算を実装
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 偏差）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio 等（ATR の NULL 伝播制御含む）
      - calc_value: PER（EPS が 0 または NULL の場合は None） / ROE（raw_financials から最新レコード）
    - DuckDB SQL を活用した効率的な実装、データ不足時は None を返す設計
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランキング（rank）、
      ファクター統計サマリー（factor_summary）を実装
    - 特長:
      - horizons のバリデーション（1..252）
      - Spearman（ランク相関）による IC 計算、同順位は平均ランクで処理
      - 外部ライブラリに依存せず、標準ライブラリと DuckDB のみで完結

- その他
  - src/kabusys/ai/__init__.py と src/kabusys/research/__init__.py による public API の整理・再エクスポート
  - DuckDB を主要なローカル分析ストアとして利用する設計に統一

Changed
- 初回リリースのため変更履歴なし

Fixed
- 初回リリースのため修正履歴なし

Removed
- 初回リリースのため削除履歴なし

Security
- 初回リリースのためセキュリティ関連の変更なし

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策: 多くの処理で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）
- DuckDB 前提: 全ての分析・ETL 機能は DuckDB 接続を受け取り、価格・ニュース・財務データを参照する
- フェイルセーフ:
  - OpenAI API 呼び出し失敗時はスコアを 0.0 にフォールバックして処理継続（例外を上げない箇所あり）
  - ETL / DB 書き込みはトランザクション制御（BEGIN/COMMIT/ROLLBACK）で安全に実行
- テスト容易性:
  - OpenAI 呼び出し箇所は内部関数を patch できるように設計
  - 環境変数自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意

今後の予定（省略可能）
- strategy / execution / monitoring の実装拡充（公開 API に含まれるが未提示の詳細実装を追加）
- ユニットテスト・統合テスト増強、CI パイプライン整備
- 追加の品質チェック (quality モジュールの充実) と観測ダッシュボード

この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はリリース担当者が変更内容を確認・修正してください。