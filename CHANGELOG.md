# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルには、リポジトリ内のコードベースから推測した機能追加・設計方針・重要な実装ノートをまとめています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買システム「KabuSys」のコアモジュール群を実装。

### 追加
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開インターフェースに data / strategy / execution / monitoring を定義。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して判定（CWD に依存しない実装）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - コメント・空行を無視。
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォート無しの行でのインラインコメント判定（直前がスペース/タブ の場合のみ）に対応。
  - _load_env_file による読み込み時の上書き制御（override/protected）をサポート。
  - Settings クラスでアプリ設定をプロパティ経由で提供。
    - J-Quants / kabuAPI / Slack / データベースパス（DuckDB/SQLite）/環境（development/paper_trading/live）/ログレベル等のプロパティを用意。
    - 必須環境変数未設定時は ValueError を送出（_require）。
    - env・log_level の入力検証（許容値のチェック）を実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols テーブルからニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出。
    - 特徴:
      - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC で変換）を対象（calc_news_window を提供）。
      - バッチサイズ、記事数・文字数制限（過度なトークン肥大化対策）。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ（最大回数設定）。
      - レスポンスの厳密なバリデーション（JSON 抽出、results list、code/score の検証、既知コードのみ採用、スコアのクリップ）。
      - 部分成功時に既存スコアを保護するため、書き込みは対象コードのみ DELETE → INSERT を行う冪等処理。
      - テスト容易性のため _call_openai_api を patch で差し替え可能。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で market_regime テーブルに保存。
    - 特徴:
      - ma200_ratio の計算（ルックアヘッドを防ぐため target_date 未満のデータのみ使用）。データ不足時は中立（1.0）へフォールバック。
      - マクロニュース抽出（キーワードマッチング）と LLM による macro_sentiment 評価（gpt-4o-mini、JSON Mode）。
      - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフな実装。
      - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、例外時には ROLLBACK を試行）。
      - テスト用に _call_openai_api を差し替え可能。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Data（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）をラップする営業日判定ユーティリティを実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB に値がある場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
      - 最大探索日数による安全策（_MAX_SEARCH_DAYS）。
      - 夜間バッチ calendar_update_job により J-Quants から差分取得 → market_calendar へ冪等保存（fetch/save 関数は jquants_client を利用）。バックフィル・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを提供（pipeline.ETLResult を etl モジュールで再エクスポート）。
    - ETLResult は取得/保存件数、品質チェック結果、エラー情報などを保持し、to_dict() で直列化可能。
    - 差分取得用ユーティリティ（テーブルの最大日付取得など）と市場カレンダー調整ヘルパーを実装。
    - 設計方針として「営業日単位での差分更新」「バックフィルによる後出し修正吸収」「品質チェックは収集して呼び出し元に委ねる」を採用。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）などを DuckDB 上の SQL と Python ロジックで計算。
    - 欠損・データ不足時の挙動（None を返すなど）を明確に定義。
    - 出力は各銘柄について date/code を含む dict のリスト。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（スピアマンランク相関）計算、ファクター統計サマリー、ランク変換ユーティリティ等を提供。
    - pandas 等の外部依存を持たず標準ライブラリのみで実装。
    - rank 関数は同順位を平均ランクで処理（丸めにより ties の検出漏れを防ぐ）。

### 変更・設計ノート
- 全体設計
  - ルックアヘッドバイアス防止のため、関数内で datetime.today()/date.today() を参照せず、呼び出し側から target_date を与える設計を採用。
  - DuckDB を主要な分析用 DB として採用し、直接 SQL を用いることで高いパフォーマンスと DB 側の集計機能を活用。
  - API 呼び出し周りはフォールバック/フェイルセーフを重視（LLM/API の失敗でもシステム全体が停止しない）。
  - DB 書き込みは可能な限り冪等化（DELETE → INSERT、ON CONFLICT など）して部分失敗時のデータ保護を意識。
  - テスト容易性: OpenAI 呼び出しをラップする内部関数に patch を当てられるようにしている。

### 既知の制限 / 注意点
- OpenAI キー必須: score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY が必要で、未設定時は ValueError を送出する。
- DuckDB バインドの制約: executemany に空リストを渡せないバージョン互換性への対処（呼び出し前に空チェックを実施）。
- News NLP の出力形式は厳密な JSON を期待しているが、稀に余計なテキストが混ざるケースに対しては最外側の {} を抽出して復元するロジックを実装している。
- .env パーサは多くのケースを処理するが、全ての corner case を網羅するものではない（複雑な shell 構文は想定外）。

### セキュリティ
- 環境変数や API キーは OS 環境変数を保護する仕組み（protected set）を導入して .env での上書きを制御可能。

### 削除
- なし

### 修正
- なし（初回リリース）

---

開発者向け注記:
- 実装の詳細やパラメータ（リトライ回数、ウィンドウ幅、重み付け等）はソース内の定数で管理されています。挙動変更が必要な場合は該当モジュール内の定数を調整してください。
- 今後のリリースでは、テスト補助用のスタブ・モック実装、OpenAI のモデル選択の外部化、より柔軟なカレンダーフェールバック設定などを検討してください。