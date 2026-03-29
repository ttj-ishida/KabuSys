Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。フォーマットは "Keep a Changelog" に準拠しています。

注: このリポジトリはバージョン 0.1.0 として初回公開されています。

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース。以下の主要機能を追加。
  - パッケージ基盤
    - kabusys パッケージの初期化（__version__ = "0.1.0"）。
    - パッケージ内モジュールのエクスポート管理（data, strategy, execution, monitoring）。

  - 設定・環境変数管理（kabusys.config）
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートの検出は .git または pyproject.toml ベース）。
    - .env のパース機能を独自実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理など）。
    - .env と .env.local の読み込み順序（OS環境変数 > .env.local > .env）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 必須環境変数検査用の _require() 実装（未設定時は ValueError を送出）。
    - 各種設定プロパティを提供:
      - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
      - kabuステーション: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
      - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
      - 環境: KABUSYS_ENV 検証（development / paper_trading / live）
      - ログレベル: LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - ユーティリティプロパティ: is_live, is_paper, is_dev

  - AI モジュール（kabusys.ai）
    - ニュース NLP（kabusys.ai.news_nlp）
      - raw_news および news_symbols を集約し、OpenAI（gpt-4o-mini、JSON モード）で銘柄ごとのセンチメントスコアを計算して ai_scores テーブルへ書き込む。
      - ウィンドウ定義: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して処理）。
      - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたり最大記事数・文字数制限、JSON レスポンスの堅牢なバリデーションを実装。
      - エラー耐性: レート制限/ネットワーク断/タイムアウト/5xx に対する指数バックオフでのリトライ。非再試行エラーはスキップして継続。API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を参照。
      - DuckDB の executemany に対する互換性対策（空リストを渡さない）。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次で market_regime テーブルへ冪等的に書き込む。
      - マクロニュース抽出はキーワードベース、LLM 呼び出しは gpt-4o-mini（JSON）を使用。API 失敗時は macro_sentiment を 0.0 とするフェイルセーフ。
      - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK 処理。
    - 両モジュール共通: OpenAI 呼び出しは内部で分離実装しており、テスト時にモック可能。

  - データ処理 / ETL / カレンダー（kabusys.data）
    - 市場カレンダー管理（kabusys.data.calendar_management）
      - market_calendar を参照する営業日・SQ 判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
      - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバック。
      - calendar_update_job により J-Quants API から差分取得し冪等保存。バックフィル、健全性チェックを実装。
    - ETL パイプライン（kabusys.data.pipeline / etl）
      - ETLResult データクラスを公開（取得数 / 保存数 / 品質検査結果 / エラー情報などを含む）。
      - 差分更新、バックフィル、品質チェックの設計方針を実装（品質チェックは検出しても ETL を中断しない）。
    - jquants_client と quality モジュールと連携する設計（実際の API クライアント実装は別モジュール想定）。

  - リサーチ / ファクター計算（kabusys.research）
    - 提供関数（再エクスポート含む）:
      - ファクター計算: calc_momentum, calc_value, calc_volatility
        - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
        - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率
        - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）
      - 特徴量探索: calc_forward_returns（任意ホライズンでの将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（統計量）、rank（同順位は平均ランク）
      - ユーティリティ: zscore_normalize は kabusys.data.stats から再エクスポート
    - 設計方針: DuckDB 接続を受け取り prices_daily / raw_financials のみ参照、ルックアヘッドを避ける実装。

Changed
- 初回リリースのため変更履歴はなし。

Fixed
- 初回リリースのため修正履歴はなし。

Security
- 環境変数の読み込みは保護されたキーセット（OS 環境変数）を尊重する実装。自動読み込みを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）あり。
- OpenAI API キーは関数引数で注入可能かつ環境変数 OPENAI_API_KEY を参照。未設定時は明示的にエラーを出す挙動。

Notes / 使用上の注意
- OpenAI 連携機能を利用する場合、OPENAI_API_KEY（または各関数の api_key 引数）を設定する必要があります。
- AI モジュールは gpt-4o-mini の JSON Mode を前提とした出力パース実装を行っています。LLM 出力が仕様どおりでない場合はスコア取得をスキップしフォールバック（0.0 または空）します。
- DuckDB を使用する想定であり、主要テーブル名（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols など）に依存します。初期 DB ファイルパスは環境変数（DUCKDB_PATH 等）で上書き可能です。
- ルックアヘッドバイアス回避のため、日付関連処理は内部で date.today()/datetime.today() を参照しない設計が採用されています（target_date ベースの計算）。
- API エラーに対してはリトライやフェイルセーフ（無害なデフォルト値）を適用しており、部分失敗時に既存データを不必要に上書きしない工夫（コード絞り込み DELETE → INSERT など）を行っています。

今後の予定（例）
- strategy / execution / monitoring モジュールの具現化（現状はパッケージ名の準備のみ）。
- テストカバレッジ拡充、外部 API クライアント実装と統合テスト。
- ドキュメント（Usage, API リファレンス、DB スキーマ）の整備。

---
注: 本 CHANGELOG はコードベースから推測して作成した初回リリースの要約です。実装の補足や修正がある場合は随時更新してください。