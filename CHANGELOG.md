# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を追加しました。

### 追加
- パッケージ初期化
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージトップで public モジュールを明示的にエクスポート（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。
  - .env / .env.local の自動読み込み（OS 環境変数を保護、.env.local は上書き）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env ファイルパーサを実装：
    - `export KEY=val` 形式対応、クォート文字とバックスラッシュエスケープに対応、インラインコメント処理のルールを明示。
  - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等のプロパティを取得）。
    - 必須項目取得時は未設定で ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - duckdb/sqlite のデフォルトパスを設定。

- データ関連（kabusys.data）
  - カレンダー管理（calendar_management）:
    - market_calendar テーブルに基づく営業日判定 API を提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB が未取得のときは曜日ベース（週末）でフォールバック。
    - JPX カレンダー差分フェッチ → DB 更新を行う夜間ジョブ calendar_update_job を実装（J-Quants クライアント経由、バックフィル・健全性チェックあり）。
  - ETL パイプライン（pipeline）:
    - DataPlatform 設計に基づく差分取得→保存→品質チェックの土台を実装。
    - ETL 実行結果を表すデータクラス ETLResult を追加（target_date / fetched/saved カウント / quality_issues / errors を含む、has_errors などのユーティリティを提供）。
  - etl モジュールで ETLResult を再エクスポート（kabusys.data.etl）。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials を用いた PER / ROE の計算（target_date 以前の最新財務データを使用）。
    - いずれも DuckDB 上の prices_daily / raw_financials を参照し、ルックアヘッドを防ぐ設計。
  - 特徴量解析（feature_exploration）:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード3件未満は None）。
    - factor_summary: 指定カラムの基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクとするランク付けユーティリティ。
  - research パッケージで主要関数を再エクスポート。

- AI / NLP（kabusys.ai）
  - ニュース NLP（news_nlp）:
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算する calc_news_window。
    - raw_news + news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとの sentiment（ai_score）を計算する score_news。
    - API 呼び出しは JSON Mode（厳密な JSON 出力を期待）を使用し、バッチ処理・最大記事数/文字数トリム、最大バッチサイズ、リトライ（429/ネットワーク/5xx）等のロジックを実装。
    - レスポンスのバリデーション、数値クリップ（±1.0）、部分失敗時の DB 更新保護（対象コードのみ DELETE → INSERT）などの安全対策を実装。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロ経済ニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出する score_regime を実装。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント算出（JSON 出力想定）、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）、最終的に market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - OpenAI 呼び出しは news_nlp とは別実装とし、モジュール結合を避ける設計。
  - ai パッケージで score_news をエクスポート。

### 変更（設計上の注意 / 実装方針）
- ルックアヘッドバイアス防止のため、いかなる関数も datetime.today() / date.today() に依存せず、全て target_date を明示的に受け取る設計。
- DuckDB に対する互換性配慮（executemany の空リスト回避、日付型の取り扱い、リストバインドの回避等）を実装。
- OpenAI 呼び出しはタイムアウト・レート制限・サーバーエラーに対してエクスポネンシャルバックオフでリトライするフェイルセーフ設計。ただし各モジュールは API 失敗時に例外をそのまま投げずフォールバックまたは空スコア化する方針（運用耐性向上）。
- 設定読み込み順と保護（OS 環境変数優先、.env → .env.local）を明確化。

### 修正 / 既知の動作
- .env パーサはクォート内部のバックスラッシュエスケープを考慮する実装（実運用での環境変数パース整合性を改善）。
- 各種 DB 書き込みは冪等性を意識（DELETE → INSERT や ON CONFLICT 相当の保存を意図）。

### 非互換 / 破壊的変更
- なし（初回リリース）。

### セキュリティ
- 外部 API キー（OpenAI 等）は引数注入または環境変数経由でのみ解決。必要なキーが見つからない場合は明示的に ValueError を送出して安全性を確保。

## 未定 / 今後の予定（メモ）
- strategy / execution / monitoring の具現化と発注周りの安全ガード・シミュレーション機能の追加。
- ai モジュールのテスト利便性向上（API 呼び出し抽象化／モック拡張）。
- 品質チェックモジュールの実装拡張（quality モジュールのルール追加）。
- ドキュメント（API 使用法・設定例・運用ガイド）の整備。

---

（注）本 CHANGELOG は提供されたコード内容から推測して作成した要約です。実際のリリースノートはリポジトリのコミット履歴やリリース管理ポリシーに基づいて調整してください。