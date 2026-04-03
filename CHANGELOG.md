# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0（初期リリース）

## [Unreleased]

## [0.1.0] - 2026-04-03
初期リリース。日本株のデータ取得・ETL・研究（リサーチ）・AIによるニュース解析・市場レジーム判定・カレンダー管理・環境設定ユーティリティを含む一連のモジュール群を公開。

### 追加
- パッケージ基礎
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
  - パッケージの公開 API を `__all__` により定義（data, strategy, execution, monitoring）。

- 環境設定 / config
  - .env ファイルおよび環境変数を読み込む自動ローダーを実装。プロジェクトルートは `.git` または `pyproject.toml` を起点に検索するため、CWD に依存しない設計。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなしの行中コメント処理（直前がスペース/タブの場合に # をコメントとみなす）。
    - 無効行（空行・コメント行）を無視。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - 環境変数保護機構を導入し、既存の OS 環境変数を保護した上で `.env.local` を上書き可能に。
  - Settings クラスを提供し、以下の設定をプロパティで取得:
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB / SQLite）/ 監視関連（PID ファイル・kill フラグ・しきい値）/ システム設定（KABUSYS_ENV, LOG_LEVEL など）
  - 必須環境変数未設定時は明示的に ValueError を送出する `_require` を実装。
  - `KABUSYS_ENV` と `LOG_LEVEL` の妥当性検査を実装。

- データ / data
  - ETL 結果を表す `ETLResult` データクラスを追加（保存件数・品質問題・エラー等を集約）。
  - ETL パイプラインモジュール（差分取得／保存／品質チェックの実装方針とユーティリティ）を実装。
    - 差分更新・バックフィル・品質チェックの設計を実装。
    - DuckDB を利用する実装（テーブル存在チェック / 最大日付取得ユーティリティなど）。
  - calendar_management:
    - JPX マーケットカレンダー管理（市場カレンダーの取得・保存・営業日判定ロジック）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった公開 API を提供。
    - market_calendar が未登録のときは曜日ベース（土日除外）でフォールバックする堅牢設計。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。

- AI / ai
  - ニュース NLP スコアリング（news_nlp）:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）の JSON mode でセンチメント（-1.0〜1.0）を生成。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を行い、UTC 時刻で DB クエリを実行する `calc_news_window` を実装。
    - バッチサイズ (_BATCH_SIZE=20) ごとのチャンク処理、1銘柄あたりの記事数と文字数上限（トリム）によるトークン過大対策を導入。
    - 429/ネットワーク断/タイムアウト/5xx の場合は指数バックオフでリトライ。その他エラーは安全にスキップして継続。
    - OpenAI レスポンスの堅牢なバリデーション（JSON パース、余計な前後テキストの復元、結果構造検査、未知コード無視、数値検査）を実装。
    - スコアを ±1 にクリップし、部分失敗時は影響範囲を限定するため書き込みは対象コードのみ DELETE→INSERT（executemany）で置換。
    - raw_news.datetime が UTC で保存されている前提。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算時にはルックアヘッドバイアスを防ぐため target_date 未満のデータのみを利用。データ不足時は中立(1.0)を採用。
    - マクロニュース取得（キーワードフィルタ）と OpenAI 呼び出しは分離された実装。API 失敗時は macro_sentiment=0.0 としてフェイルセーフに処理を継続。
    - レジーム合成スコアをクリップし閾値でラベリング、market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - OpenAI API 呼び出しはリトライや 5xx 判定に対応。

- Research / research
  - ファクター計算（factor_research）:
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等を計算する関数を実装。DuckDB の SQL ウィンドウ関数を活用し高速に計算。
    - 欠損やデータ不足時は None を返す設計。
  - 特徴量探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns、horizons 指定可）、IC（Spearman のランク相関）計算、rank ユーティリティ、factor_summary（基本統計量）を実装。
    - pandas 等の外部ライブラリに依存せず純標準ライブラリ + DuckDB のみで実装。
  - 公開 API を __init__ でまとめてエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更（設計上の注意・実装上の重要点）
- DB 書き込みの冪等性を重視:
  - AI スコア・レジーム書き込みなどは対象日/銘柄を絞って DELETE→INSERT を行い部分失敗時に既存データを保護。
- ルックアヘッドバイアス防止:
  - すべての「日次」ロジック（ニュースウィンドウ、MA 計算、ETL 等）は内部で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を与える設計。
- DuckDB 互換性に配慮:
  - executemany に空リストを渡さないチェック等、DuckDB のバージョン差異に備えた実装。
- OpenAI 連携について:
  - OpenAI クライアントと API キー注入をサポート（api_key 引数優先、未指定時は環境変数 OPENAI_API_KEY を参照）。未設定時は ValueError を送出。
  - JSON mode のレスポンスを前提にしているが、パース耐性（前後テキストの復元等）を持たせている。

### 修正（実装上の例外処理 / フェイルセーフ）
- API 呼び出し失敗や JSON パースエラーは原則例外を伝播させず、警告ログを出して安全にフォールバック（macro_sentiment=0.0、当該チャンクスキップ等）することでパイプライン全体の停止を防止。
- データ不足（MA 等）に対しては None または中立値を返し、上位処理が扱えるようにしている。

### 既知の制限 / TODO（初期版の注意点）
- raw_financials から PBR・配当利回り等は現バージョンでは未実装（PER/ROE のみ）。
- raw_news.datetime は UTC で保存されている前提。データ収集側で UTC 保存が必要。
- OpenAI のレスポンスに対しては堅牢に処理するが、モデルや SDK の将来変更（レスポンス構造・例外クラス名等）により追加対応が必要となる可能性あり。
- DuckDB の特定バージョン間の挙動差（型バインドや executemany）に依存する箇所があるため、運用時はターゲットの DuckDB バージョンでの検証を推奨。
- ETL の品質チェック（quality モジュール）は検出結果を集める設計で、重大な品質問題が出ても ETL を継続する（呼び出し元での判断を想定）。

### セキュリティ
- 特記事項なし（このリリースでは機密情報の扱いに関する明示的な機能追加はない）。OpenAI API キーや各種トークンは環境変数経由で管理することを想定。

---

注: この CHANGELOG は提供されたソースコードの実装とドキュメント文字列を基に推測して作成した初期リリース向けのまとめです。リリースノートや運用ドキュメントとして利用する際は、実際のリポジトリ履歴・テスト結果・外部依存バージョンを合わせて確認してください。