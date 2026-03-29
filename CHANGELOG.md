KEEP A CHANGELOG
すべての重要な変更をこのファイルに記録します。
このプロジェクトは「Keep a Changelog」の規約に従って管理されています。

Unreleased
- （なし）

[0.1.0] - 2026-03-29
Added
- 基本パッケージ初期リリースを追加。
  - パッケージ情報:
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - 公開モジュール: data, research, ai, execution, monitoring（package __all__ を通して公開）

- 環境設定 / 読み込み機能（kabusys.config）を実装。
  - .env / .env.local からの自動読み込み機能を実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない実装。
  - 読み込み上書き制御（override）と OS 環境変数保護（protected keys）に対応。
  - .env パースのロバスト化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理
    - クォートなし行のインラインコメントの扱いを適切に処理
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - Settings クラスで各種必須環境変数を取得するプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。

- AI 関連機能（kabusys.ai）を追加。
  - news_nlp モジュール:
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - チャンク処理（デフォルト 20 銘柄/リクエスト）、記事数/文字数トリム、JSON Mode を使用した出力整形、レスポンスのバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx などを対象とした指数バックオフとリトライ処理を実装。
    - レスポンスの堅牢なパース（余分な前後テキストから JSON を抽出する補正含む）およびスコアクリッピング（±1.0）。
    - DuckDB への書き込みは部分失敗に耐える設計（取得済みコードだけを DELETE → INSERT で置換、executemany の空リスト回避）。
    - テスト容易性のため、OpenAI 呼び出し箇所を patch 可能に設計（_call_openai_api を差し替え可能）。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。

  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタし、最大 N 件（デフォルト 20）を LLM に渡して macro_sentiment を算出。
    - OpenAI 呼び出しはリトライや 5xx 判定などを取り扱う堅牢な実装。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ使用、datetime.today() などを参照しない）。
    - 結果は DuckDB の market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 正常時に 1 を返す。

- データ基盤機能（kabusys.data）を追加。
  - calendar_management モジュール:
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装。
    - 営業日判定・前後営業日取得・期間内営業日取得・SQ 判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーが存在しない場合の曜日ベースのフォールバック。
    - next/prev/get で DB 値優先 → 未登録日は曜日基準フォールバックで一貫性を保つ実装。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等保存。バックフィルと健全性チェックを実装。
    - 最大探索日数やバックフィル日数などを定数で管理（安全策あり）。

  - pipeline / ETL（kabusys.data.pipeline / etl）:
    - ETLResult データクラスを実装して ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
    - 差分更新、保存（jquants_client の save_*）、品質チェック（quality モジュールを想定）を行うパイプライン設計方針を実装（詳細ロジックは pipeline 内で扱う）。
    - _get_max_date 等の DB ヘルパーとテーブル存在確認を実装。
    - デフォルトのバックフィル日数やカレンダー先読み日数を定義。
    - etl モジュールは ETLResult を再エクスポート。

  - ETL や calendar モジュールは DuckDB と互換性を保つための注意（executemany の空リスト回避、DuckDB の日付値変換等）を実装。

- リサーチ機能（kabusys.research）を追加。
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、バリュー（PER、ROE）、ボラティリティ/流動性（20日 ATR、平均売買代金、出来高比率）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_value, calc_volatility）。
    - データ不足時は None を返す設計。
    - 計算は SQL（DuckDB）中心で実装し、外部ネットワークアクセスは行わない。

  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）を実装。複数ホライズンに対応し、入力検証を実施。
    - IC（情報係数）計算（calc_ic）: スピアマンのランク相関を自前実装（外部ライブラリ非依存）。同順位の取り扱いは平均ランクを使用。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を提供。
    - 実装は標準ライブラリのみで完結するように設計。

- テストおよび運用を意識した設計上の配慮を多数導入。
  - ルックアヘッドバイアス防止の徹底（datetime.today()/date.today() をスコアリング関数内部で参照しない）。
  - OpenAI 呼び出しの差し替え可能設計（ユニットテストで patch しやすい）。
  - API 失敗時はフェイルセーフで継続（多くの箇所で 0.0 や空結果でフォールバック）、部分失敗時に既存データを保護する DB 書き込み設計。

Security
- （このリリースで特筆すべきセキュリティ修正はありません。API キーやパスワード等の必須設定は Settings を通じて環境変数から取得する設計です。）

Deprecated
- （なし）

Removed
- （なし）

Notes / 既知の制約
- DuckDB のバージョン依存や executemany の挙動に注意（コード内に回避策あり）。
- OpenAI の呼び出しは GPT JSON Mode を前提とするため、将来の API 変更があれば修正が必要になる可能性あり。
- 一部機能（例: PBR や配当利回り）は現バージョンでは未実装（calc_value の注意記載）。

（備考）
- 本 CHANGELOG はコードベースの実装内容から推測してまとめています。実際のリリースノート作成時は行った変更・マージ履歴・リリースチケットに基づき調整してください。