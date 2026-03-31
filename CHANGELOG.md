# CHANGELOG

すべての notable な変更はこのファイルに記録されます。  
このプロジェクトはセマンティック バージョニングを使用しています。  
詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。内部設計方針に基づくコア機能群を実装・公開しました。

### 追加
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = "0.1.0" を定義し、主要サブパッケージ（data, research, ai, monitoring, strategy, execution 等）を __all__ に列挙。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルと OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 高度な .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - .env 読み込み時に OS 環境変数を保護する protected キーの仕組みを実装（.env.local は override=True により上書き可能だが protected は除外）。
  - Settings クラスを追加し、アプリケーションで使用する設定値をプロパティで提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時は ValueError）。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH にデフォルト値を提供。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーションを実装。
    - is_live / is_paper / is_dev ヘルパーを追加。

- AI 関連 (kabusys.ai)
  - ニュースセンチメント（ニュースNLP）: score_news 実装
    - raw_news / news_symbols を集約して銘柄ごとにニュースを統合し、OpenAI（gpt-4o-mini）へバッチ送信してスコアを取得。
    - 時間ウィンドウは「前日 15:00 JST 〜 当日 08:30 JST」を想定（UTC 変換済み）。
    - バッチサイズ、トリム最大文字数、記事数上限などトークン肥大化対策を実装。
    - API 呼び出しに対するリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで処理。
    - レスポンスの堅牢なバリデーションと数値クリッピング（±1.0）。
    - DuckDB への冪等書き込み（DELETE → INSERT）で部分失敗時の既存データ保護を実装。
    - テスト容易性のため _call_openai_api をパッチ可能に設計。
  - 市場レジーム判定: score_regime 実装
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - OpenAI 呼び出しは独立実装で、API失敗時は macro_sentiment=0.0 としてフェイルセーフ継続。
    - レジーム算出後は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に保存。
    - API キー注入（引数）または環境変数 OPENAI_API_KEY での解決をサポート。未設定時は ValueError を送出。

- データ基盤 (kabusys.data)
  - ETL パイプラインの公開 API: ETLResult クラスを追加（kabusys.data.pipeline.ETLResult を再エクスポート）。
  - pipeline モジュール:
    - 差分更新、バックフィル、品質チェックを想定した ETLResult データクラスを実装（品質チェック結果の集約、エラー有無判定など）。
    - DuckDB の最大日付取得ユーティリティ、テーブル存在チェックなどを実装。
    - market_calendar などのカレンダー関連ヘルパーを想定した設計。
  - calendar_management モジュール:
    - JPX カレンダー管理（market_calendar テーブル）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録値優先、未登録日の曜日ベースフォールバック、検索上限 (_MAX_SEARCH_DAYS) の実装。
    - calendar_update_job を実装し、J-Quants クライアントからの差分取得・バックフィル・安全性チェック（未来日異常検出）・保存処理を実装。
    - J-Quants クライアント呼び出しは外部モジュール（kabusys.data.jquants_client）を利用する設計。

- リサーチ機能 (kabusys.research)
  - ファクター計算: calc_momentum / calc_volatility / calc_value を実装
    - momentum: 1m/3m/6m リターン、200 日 MA 乖離（データ不足時は None / 中立扱い）を計算。
    - volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出（欠損制御あり）。
    - value: raw_financials から最終財務データを取得して PER / ROE を計算。
    - DuckDB のウィンドウ関数を活用した実装と、営業日スキャンバッファを設計。
  - 特徴量探索: calc_forward_returns / calc_ic / rank / factor_summary を実装
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（有効レコード数判定あり）。
    - rank: 同順位は平均ランクにする手法を実装（浮動小数点丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを実装。
  - research パッケージの __init__ で主要関数を再エクスポート。

### 変更（設計上の重要点）
- バイアス防止設計
  - 全てのデータ処理・スコアリング関数は datetime.today() / date.today() を内部で参照しない設計（外部から target_date を注入）。これによりルックアヘッドバイアスを防止。
- フェイルセーフ優先
  - 外部 API（OpenAI / J-Quants）失敗時は例外を投げずフォールバック値（例: macro_sentiment=0.0、スコア未取得扱い）で継続する実装方針を採用。
- DuckDB 互換性に関する注意
  - DuckDB 0.10 の挙動を考慮した実装（executemany に空リストを渡さない等）。
- テスト容易性
  - OpenAI 呼び出し部は内部関数（_call_openai_api）をパッチ可能にし、ユニットテストで簡単にモックできるように設計。

### 修正（既知の制約・挙動）
- OpenAI API キー未設定時は score_news / score_regime が ValueError を投げる（利用前に api_key 引数または環境変数 OPENAI_API_KEY を設定する必要あり）。
- データ不足（例: 200 日分の価格がない等）の際は一部ファクターが None または中立値（1.0 や 0.0）で処理される。
- ai スコアは ±1.0 にクリップされる。
- calendar_update_job は J-Quants からの取得失敗や保存失敗時に 0 を返し、ログ出力する。

### 既知のセキュリティ配慮
- .env 読み込みで OS 環境変数を保護する仕組みを導入（.env による上書きを制御）。
- 機密トークン（OpenAI / J-Quants / Slack 等）は必須設定項目として環境変数経由で管理する前提。

## 既知の TODO / 今後の改善予定（コードから推測）
- ai モジュールでのモデル選択や温度等の可変化（現在は gpt-4o-mini 固定）。
- PBR / 配当利回り等のバリューファクター追加（calc_value の拡張）。
- calendar_update_job の失敗時により詳細なリトライ戦略を追加。
- より詳細な品質チェック・アラート（quality モジュールの拡張）。
- monitor / execution / strategy モジュールの具体的実装（現時点でインターフェース中心）。

---

（注）上記 CHANGELOG は提示いただいたソースコードの内容とドキュメント文字列から推測して作成しています。実際のリリースノートとして使用する場合は、コミット履歴や CHANGELOG 用の管理方針に合わせて調整してください。