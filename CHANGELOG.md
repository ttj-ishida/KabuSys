CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
バージョン表記は PEP 440 に準拠します。

[Unreleased]
-------------

（現在の作業ブランチ向けの未リリース変更はここに記載します）

[0.1.0] - 2026-03-31
-------------------

初回公開リリース。kabusys パッケージの基礎機能群を実装しました。主な追加点・設計方針・注意点を以下にまとめます。

Added
- パッケージ基盤
  - kabusys パッケージを追加。__all__ に ["data", "strategy", "execution", "monitoring"] を公開。
  - バージョン: 0.1.0 を設定。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供（settings インスタンスを公開）。
  - 自動 .env 読み込み:
    - プロジェクトルートの自動検出 (.git または pyproject.toml を基準) により .env / .env.local をロード。
    - OS 環境変数を保護する protected 機構、.env.local による上書き処理に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等に対応。
  - 必須キー取得用の _require() 実装。未設定時は ValueError を送出。
  - 各種プロパティを提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境判定等）。env と log_level の検証を実行。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを評価して ai_scores テーブルへ書き込む。
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window で提供。
    - バッチ送信（最大 20 銘柄）、記事数/文字数トリミング、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - API 呼び出し箇所（_call_openai_api）はテストで差し替え可能。
    - OpenAI API キーが未設定の場合は ValueError を送出。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照し、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - マクロ記事がある場合のみ LLM 呼び出しを行い、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出しは独自実装で、テスト用の差し替えポイントを提供。
    - OpenAI API キーが未設定の場合は ValueError を送出。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルがない場合は曜日ベース（平日＝営業日）のフォールバック。
    - calendar_update_job: J-Quants クライアント経由でカレンダーを差分取得し market_calendar を更新（バックフィル・健全性チェック実装）。
  - pipeline / etl:
    - ETLResult データクラスを公開（etl パイプラインの実行結果集約用）。
    - ETL の設計方針（差分更新、バックフィル、品質チェック、idempotent 保存）を実装方針としてコードに反映。
  - jquants_client / quality 等との連携ポイントを想定した設計。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を算出。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損なら None）。
    - 全関数は DuckDB を用いた SQL 実行により実装。結果は (date, code) をキーとする辞書リストで返却。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を算出、ホライズンの妥当性チェックあり。
    - calc_ic: スピアマンのランク相関（IC）を実装。結合・欠損除外・最小レコード数チェックを行う。
    - rank: 平均ランク（同順位は平均ランク）を算出（丸め処理で ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計ユーティリティ。
  - すべて標準ライブラリ + DuckDB で実装（pandas 等に依存しない）。

Changed / Design decisions
- ルックアヘッドバイアス防止:
  - 各種モジュール（news_nlp, regime_detector, research 等）は内部で datetime.today()/date.today() を直接参照しない設計。すべて target_date を引数で受けることで再現性を確保。
  - DB クエリは target_date 未満（排他）等の条件を明示的に使用し、将来データを参照しないよう配慮。
- OpenAI 呼び出し:
  - JSON Mode を利用し厳密な JSON を期待するが、パース失敗時に補完（最外の { } 抽出）やフェイルセーフ（0.0 やスキップ）で耐性を持たせる。
  - リトライ戦略（429/接続断/タイムアウト/5xx）とバックオフを実装。
- DuckDB 互換性:
  - executemany に空リストを渡さないチェック（DuckDB 0.10 の制約への対処）。
  - idempotent な DB 書き込み（DELETE → INSERT、または ON CONFLICT を想定）とトランザクション制御（BEGIN/COMMIT/ROLLBACK）。
- テスト容易性:
  - OpenAI の呼び出し箇所をモジュール内部でラップしており、unittest.mock.patch などで差し替え可能。
  - 明示的に ValueError を投げる箇所を定義し、外部キー未設定時の挙動を明確化。

Fixed
- （初回リリースのため既知のバグ修正履歴はありません。コード内に堅牢性のための多くのフォールバック処理・ログ出力を実装。）

Removed
- （該当なし）

Security
- 環境変数ロード時の挙動:
  - OS 環境変数はデフォルトで保護され、.env による意図しない上書きを避ける設計。
  - 自動ロードをオフにする KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

Known limitations / Notes
- 実行に必要な環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）は未設定時に ValueError を送出する場所があります。README/.env.example を参照して設定してください。
- OpenAI 呼び出しは外部 API に依存するため、API レートリミットや料金に注意してください。API 呼び出し失敗時はフェイルセーフ（スコア 0.0 またはスキップ）で継続する設計です。
- calendar_update_job や ETL は jquants_client の実装に依存します。実際の API 呼び出しや保存処理の挙動は jquants_client の実装に依存します。
- strategy / execution / monitoring パッケージはパッケージ公開対象として __all__ に含まれていますが、本リリースでの具体的な実装状況はコードベースの他ファイルに依存します。

謝辞
- 本リリースは DuckDB、OpenAI API（gpt-4o-mini など）を利用する研究用・運用用の基盤コード群の初期実装です。今後、テスト・ドキュメント・運用監視機能の充実を予定しています。