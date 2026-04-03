CHANGELOG
=========
※このファイルは "Keep a Changelog" の形式に準拠しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-03
--------------------

### Added
- 初期リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開インターフェース: kabusys.data, kabusys.ai, kabusys.research, kabusys.config など主要モジュールを収録。
- 環境設定 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込みする仕組みを実装。
  - .env のパースは以下をサポート:
    - コメント行（#）/ 空行無視
    - export プレフィックス（export KEY=val）
    - シングル・ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなし値のインラインコメント検出（直前が空白またはタブの場合）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 読み込み時の上書き挙動: .env → .env.local の優先順を採用。.env.local は既存 OS 環境変数（保護セット）を上書きしない設定も可能。
  - Settings クラスによる型付きプロパティを提供（必須環境変数は _require() で検査）:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
    - 任意/デフォルト: KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 各種リソース閾値など
    - KABUSYS_ENV / LOG_LEVEL の値検証を実施（許容値以外は ValueError）
- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダーの更新バッチ (calendar_update_job) を実装（J-Quants クライアント経由で差分取得、冪等保存）。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダー情報がない場合は曜日（平日）ベースのフォールバックを採用し、一貫性を保つ設計。
    - バックフィル／先読み（lookahead）・健全性チェック・最大探索日数制限を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の収集・シリアライズ用）。
    - 差分取得、バックフィル、品質チェック（quality モジュール）を想定した ETL 設計方針を実装。
    - DuckDB テーブル存在チェックや最大日付取得等のユーティリティを実装。
  - etl モジュールの公開インターフェースを整備（ETLResult の再エクスポート）。
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - 指定日の前日 15:00 JST 〜 当日 08:30 JST を対象に raw_news と news_symbols を集約し、銘柄ごとのニュースを結合して OpenAI（gpt-4o-mini）へ送信、センチメントスコアを ai_scores テーブルへ書き込む。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1銘柄あたり文字数トリム、最大記事数制限などトークン肥大化対策を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。API レスポンスのバリデーション（JSON 抽出、results 構造チェック、コード検証、数値チェック）を実施。スコアは ±1.0 にクリップ。
    - DuckDB の executemany に対する互換性問題（空リスト渡し）を考慮し、空チェックを行った上で DELETE/INSERT を実行。
    - API キーは引数で注入可能（テスト容易性）。未設定時は環境変数 OPENAI_API_KEY を参照して例外を送出。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを 70:30 で合成し、市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロニュース抽出はマクロキーワードリストでフィルタ（最大記事数制限）。OpenAI 呼び出し失敗時は macro_sentiment=0.0 のフェイルセーフ実装。
    - LLM 呼び出しとレスポンス処理は堅牢なリトライ・エラーハンドリング（APIError のステータス解析含む）を備える。
- リサーチ / ファクター群 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などを計算（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と prices_daily を組み合わせ、PER/ROE を計算（EPS が 0/欠損時は None）。
    - 全て DuckDB 上の SQL と最小限の Python ロジックで実装（本番口座へ影響なし）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21）で将来リターンを計算。ホライズン検証とスキャン範囲の効率化あり。
    - calc_ic: スピアマンランク相関による IC 計算（結合と None 除外、最小レコード数チェック）。
    - rank / factor_summary: 同順位処理（平均ランク）や基本統計量を算出するユーティリティを実装。
  - research パッケージ入口で主要関数を再エクスポート。
- テスト容易性 / 設計上の配慮
  - OpenAI 呼び出し箇所は内部関数（_call_openai_api）を定義し、テスト時に patch 可能なよう設計。
  - datetime.today() / date.today() を直接使わない設計（ルックアヘッドバイアス回避）。
  - DB 書き込みは冪等化（DELETE→INSERT や ON CONFLICT 相当）を重視し、部分失敗時に既存データを不必要に削除しない戦略を採用。
- ロギングと警告
  - 各モジュールで情報・警告・例外時のログ出力を充実させ、フェイルセーフ時の理由をログに残す実装。

### Fixed
- DuckDB executemany の互換性を考慮し、空リストを渡さない保護ロジックを追加（空の場合は実行をスキップ）。これにより DuckDB 0.10 系でのエラー回避。

### Security
- 環境変数の必須チェック（_require）を導入し、必須トークン・パスワードが未設定の場合に早期に ValueError を発生させることで誤動作を防止。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。

### Changed
- （初回リリースのため変更履歴なし）

### Deprecated
- なし

### Removed
- なし

備考
----
- OpenAI / J-Quants / kabu ステーションなど外部サービスとの連携を行うため、実行には各種 API キーやローカル API（kabusapi）等の設定が必要です。設定は Settings クラスまたは環境変数で行ってください。
- 各関数はテストしやすいように API キー注入・内部呼び出しの差し替えポイントを用意しています。ユニットテスト時はこれらをモックしてください。