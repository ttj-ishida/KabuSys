CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」形式で記載しています。  
セマンティックバージョニングに従います。  

Unreleased
----------

- （現在なし）

0.1.0 - 2026-03-27
------------------

Added
- 初回公開リリース。KabuSys 日本株自動売買システムの基盤機能を実装。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ外部公開モジュールとして data, strategy, execution, monitoring をエクスポート。

  - 環境設定管理 (kabusys.config)
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 行パーサーは export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理をサポート。
    - .env 読み込み時の上書き制御と OS 環境変数保護（protected set）に対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティ経由で取得。必須項目は未設定時に ValueError を送出。KABUSYS_ENV と LOG_LEVEL の値検証を実装。

  - AI モジュール (kabusys.ai)
    - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
      - raw_news と news_symbols を用いて銘柄別に記事を集約し、OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信してセンチメントを算出。
      - バッチ処理（最大20銘柄/回）、1銘柄あたり最大記事数・文字数のトリム、JSON レスポンスの堅牢なバリデーションを実装。
      - API リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実施。その他のエラーは安全にスキップして継続。
      - スコアを ±1.0 にクリップ。取得したスコアのみ ai_scores テーブルへ冪等書き込み（削除→挿入）し、部分失敗時に既存データを保護。
      - calc_news_window：JST 基準でニュース収集ウィンドウ（前日15:00〜当日08:30）計算ユーティリティを提供。
      - テスト容易性のため、OpenAI 呼び出し箇所を差し替え可能（ユニットテストで patch 可能）。

    - 市場レジーム判定 (kabusys.ai.regime_detector)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
      - prices_daily から ma200_ratio を計算、raw_news からマクロキーワードでフィルタしたタイトル群を取得し、OpenAI によるマクロセンチメント評価を統合。
      - LLM 呼び出しはリトライ・バックオフ・フェイルセーフ（失敗時 macro_sentiment=0.0）を備える。
      - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。lookahead バイアスを防ぐ設計（date 比較は target_date 未満など）。

  - データプラットフォーム (kabusys.data)
    - カレンダー管理 (kabusys.data.calendar_management)
      - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装：J-Quants から取得 → market_calendar へ冪等保存（ON CONFLICT 相当）・バックフィル・健全性チェックを行う。
      - 営業日判定ユーティリティを提供：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索日数を制限して無限ループを防止。
      - market_calendar が未取得時は曜日ベース（週末除外）で一貫したフォールバックを行う。

    - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
      - 差分取得 → 保存 → 品質チェック の流れに対応する ETLResult データクラスを実装（保存件数、品質問題、エラー集約など）。
      - 保存先は jquants_client 経由で Idempotent に保存する想定。backfill_days による再取得・部分失敗保護・品質チェックの集約を設計に含む。
      - ETLResult を外部へ再エクスポート（kabusys.data.etl.ETLResult）。

    - DuckDB を前提とした各種ユーティリティと互換性処理を実装（テーブル存在チェック、日付変換など）。

  - Research モジュール (kabusys.research)
    - factor_research
      - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から最新財務を取得して PER・ROE を計算（EPS が 0/欠損 の場合は None）。
      - DuckDB SQL とウィンドウ関数を利用した効率的な実装。データ不足時は適切に None を返す。

    - feature_exploration
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。入力バリデーション（horizons は 1..252）。
      - calc_ic: ファクター値と将来リターンのランク相関（Spearman ρ）を計算。有効レコードが少ない場合は None を返す。
      - rank: 同順位は平均ランクを付与するランク関数（丸めによる ties 検出漏れ対策あり）。
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

  - 設計上の共通方針
    - ルックアヘッドバイアス回避のため、モジュール内部で datetime.today() / date.today() を直接参照しない（target_date を明示的に受け取る設計）。
    - OpenAI 等外部 API 呼び出しに対してはリトライ・バックオフ・フェイルセーフを設け、API 失敗時に例外で処理が全面停止しないよう実装。
    - DB 書き込みは冪等操作（DELETE→INSERT や ON CONFLICT 相当）で部分失敗時のデータ消失を防止。
    - テスト容易性を意識し、OpenAI 呼び出しや env 自動ロードの差し替え（mock/patch・無効化フラグ）を可能にしている。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数の読み込みにおいて OS 環境変数を保護する仕組み（protected set）を導入。API キー未設定時は明示的に ValueError を送出することで意図しない公開を防止。

Notes
- 実装は DuckDB を前提としており、OpenAI SDK（OpenAI クライアント）に依存する。実行環境では各種環境変数（OPENAI_API_KEY 等）や DB 初期化が必要です。
- 今後のリリースでは strategy / execution / monitoring 関連の注文ロジック・実行系・監視機能、テストカバレッジの追加、より詳細な品質チェックやメトリクス記録を追加予定です。