# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

- 今のところ未リリースの変更はありません。

## [0.1.0] - 2026-03-31

Added
- パッケージの初期公開
  - kabusys パッケージの公開開始。モジュール構成は data, research, ai, config, monitoring, strategy, execution などを想定したエントリポイントを提供。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロード順序: OS環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントのルールに対応。
  - 必須環境変数取得ヘルパー _require を提供し、未設定時に明確なエラーメッセージを発生。
  - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（検証）など。

- ニュース NLP / AI モジュール（kabusys.ai.news_nlp）
  - raw_news と news_symbols に基づき OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント ai_score を算出し ai_scores テーブルへ書き込む score_news を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC の naive datetime で扱う calc_news_window を提供）。
  - バッチ処理: 最大 20 銘柄ずつ送信、1銘柄あたり最大10記事・3000文字にトリム。
  - 出力は厳密な JSON（{"results":[{"code":"XXXX","score":0.0}, ...]}）を期待し、レスポンスのバリデーションと ±1.0 のクリップを行う。
  - 失敗耐性: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ、その他エラーはスキップし処理継続。
  - DuckDB への書き込みは部分失敗に備え、対象コードのみ DELETE → INSERT する冪等的な保存を実装（executemany の空リスト注意対応あり）。
  - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api をパッチ可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - ma200_ratio の計算時は target_date 未満のデータのみを参照し、ルックアヘッドバイアスを排除。
  - マクロニュースは predefined なキーワードでフィルタ（複数キーワード指定）し、該当記事がある場合にのみ LLM を呼び出す。
  - OpenAI 呼び出しは専用の内部実装を用い、モジュール間でプライベート関数を共有しない設計。
  - API 失敗時は macro_sentiment=0.0 としてフォールバックし、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターンを採用。

- データ ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
  - ETL 実行結果を表す ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラー情報を集約）。
  - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールと連携する想定）。
  - DuckDB を活用したテーブル最大日付取得等のユーティリティを提供。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーを J-Quants から差分取得して market_calendar テーブルへ冪等保存する calendar_update_job を実装。
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを実装し、DB 登録値を優先、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。
  - 最大探索範囲やバックフィル日数、健全性チェック（将来日付の異常検知）などを組み込み。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュールを実装（calc_momentum, calc_value, calc_volatility）。
    - Momentum: 約1M/3M/6M リターン、200日MA乖離（ma200_dev）。
    - Volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）。
  - 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）を実装。
    - calc_forward_returns は複数ホライズンを同時に取得する効率的なクエリを実装し、horizons の妥当性検査を行う。
    - calc_ic はスピアマンのランク相関をランク関数（平均順位 tie 処理あり）を用いて計算。
    - factor_summary は count/mean/std/min/max/median を返す。

- データユーティリティ
  - DuckDB を前提にした SQL ベースの実装を行い、外部ライブラリ（pandas 等）に依存しない設計。
  - 全関数はルックアヘッドバイアス防止のため date.today()/datetime.today() を直接参照しない方針（target_date を明示的に受け取る）。

Changed
- （初版リリースのため変更履歴はなし）

Fixed
- （初版リリースのため修正履歴はなし）

Security
- OpenAI API キー・各種トークンは環境変数経由で管理する設計。自動 .env ロード時に既存 OS 環境変数は保護される（protected keys）。

Notes / Known limitations
- OpenAI へのリクエストは gpt-4o-mini モデルの JSON mode を前提とするため、API の将来的な仕様変更に注意が必要。
- DuckDB の executemany に空リストを渡せない実装上の制約に対応するため、書き込み前に空チェックを行っている。
- news_nlp と regime_detector は OpenAI コールの内部呼び出し関数を意図的に別実装としており、テスト時はそれぞれをモックすることを想定。
- 一部のテーブル名（prices_daily, raw_news, ai_scores, market_regime, raw_financials, market_calendar 等）に依存するため、スキーマの事前準備が必要。

---

メンテナンスやバグ修正、機能追加は以降のリリースで逐次記載します。