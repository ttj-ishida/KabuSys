CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このプロジェクトはセマンティック バージョニング（https://semver.org/）に従います。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

初回公開リリース。以下の主要機能・モジュールを実装しています。

Added
-----
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）とバージョン定義: __version__ = "0.1.0"。
  - パッケージの公開 API に data, strategy, execution, monitoring を含めるエクスポート設定。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env/.env.local ファイルまたは OS 環境変数から設定を自動読み込み。
  - プロジェクトルート検出（.git または pyproject.toml を上位ディレクトリから探索）によりカレントワーキングディレクトリに依存しない読み込みを実現。
  - export KEY=val 形式、クォート／エスケープ、行内コメント処理などを考慮した .env パーサ実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数検査用 helper _require と Settings クラスを提供。以下の主要設定をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV 値検証（development, paper_trading, live）
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の簡易判定プロパティ

- AI（OpenAI）統合（src/kabusys/ai/）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ問い合わせして銘柄ごとのスコアを ai_scores テーブルへ保存。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST。UTC 変換済み）を calc_news_window で提供。
    - バッチサイズ、記事数・文字数のトリミング、レスポンス検証、±1.0 クリップ、部分成功時の安全な DB 更新（DELETE→INSERT）を実装。
    - エラー回復: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ再試行、その他はフェイルセーフでスキップ。テスト用に _call_openai_api を patch で差し替え可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成し、日次で market_regime テーブルへ冪等的に書き込み。
    - マクロ記事抽出、LLM 呼び出し（gpt-4o-mini, JSON Mode）、再試行／エラーフォールバック、スコア合成とラベル化（bull/neutral/bear）を実装。
    - Look-ahead バイアス回避の設計（target_date 未満のデータのみ参照）と、API失敗時の安全なデフォルト（macro_sentiment=0.0）。

- データプラットフォーム（src/kabusys/data/）
  - マーケットカレンダ管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定（is_trading_day）, 翌営業日/前営業日の探索(next_trading_day/prev_trading_day), 期間内営業日列挙(get_trading_days), SQ日判定(is_sq_day) を実装。
    - DB データが不完全な場合は曜日ベース（平日）でのフォールバックを行い、DB 登録がある日はそれを優先する一貫したロジックを提供。
    - JPX カレンダーの夜間差分取得と冪等保存を行う calendar_update_job を実装（jquants_client 経由）。バックフィルや健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを実装し、取得/保存件数、品質チェック結果、エラー情報の収集 API を提供。
    - 差分更新、backfill、品質チェック（quality モジュール連携）、idempotent な保存方針を反映した方針・ユーティリティを実装。
    - data.etl モジュールで ETLResult を再エクスポート。
  - DuckDB を主要なローカル DB として想定（DuckDB 接続型を引数とする関数群）。

- 研究（Research）モジュール（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR）、Value（PER, ROE）などのファクター計算関数を実装。prices_daily / raw_financials のみ参照。
    - データ不足時の None 処理やログ出力、営業日バッファスキャンの考慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン）、ランク相関での IC 計算 calc_ic（Spearman）、rank ユーティリティ、統計サマリー factor_summary を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- OpenAI API キーは引数で注入可能（テスト容易性）かつ、env 変数 OPENAI_API_KEY を参照する方式。未設定時は明示的な ValueError を送出して誤ったデフォルト挙動を防止。

Notes / 設計上の重要点
-------------------
- ルックアヘッドバイアス回避: AI/研究処理は date 引数を明示的に受け取り、内部で datetime.today() / date.today() を参照しないよう設計されています（過去データのみ参照）。
- 冪等性: DB への書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT 相当の扱いを想定）し、部分失敗時に既存データを過度に消さない実装（ai_scores の個別 DELETE など）を採用。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は例外を上位にあまり伝播させず、ログとデフォルト値で継続する箇所が多数（ただし DB 書き込み失敗は伝播させる）。
- テストフレンドリー: OpenAI 呼び出し部分は内部関数（_call_openai_api）をパッチで差し替え可能にしてあり、単体テスト時にモックしやすくしています。
- DuckDB 互換性: executemany と空配列の扱いなど DuckDB 特有の挙動に配慮した実装（空パラメータチェック等）。

既知の制限 / TODO（今後の改善候補）
---------------------------------
- strategy / execution / monitoring パッケージの公開はあるが、今回のリリースで示された範囲は主にデータ・研究・AI 部分に集中しています。取引実行周りの統合テストや安全対策（発注ガード等）は今後強化予定。
- ai.news_nlp のレスポンスバリデーションやプロンプトの堅牢化は今後のチューニング対象。
- DuckDB スキーマや jquants_client の具体的な API 契約は外部ドキュメントに依存するため、導入時はサンプルスキーマ／マイグレーションを整備予定。

--------------------------------------------------------------------------------
この CHANGELOG はコードベースの実装から推測して作成しています。実運用版リリース時はリリース日・変更内容（マイナー/パッチ）を適宜更新してください。