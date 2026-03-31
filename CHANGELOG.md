# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。  
リリース日はコードベースから推測可能な最初の公開バージョン（package __version__ = "0.1.0"）を採用しています。

## [Unreleased]

- （今後の変更点やマイナー修正・機能追加をここに記載）

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。
  - パッケージバージョン: 0.1.0。

- 環境設定 / 読み込み
  - 環境変数管理モジュールを追加（kabusys.config）。
  - プロジェクトルートを .git / pyproject.toml から自動検出して .env, .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
  - .env パースの堅牢化:
    - `export KEY=val` 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - 行末コメントの取り扱い（クォート有無で挙動を分ける）
  - Settings クラスを提供し、アプリ設定（J-Quants / kabu / Slack / DB パス / 監視設定 / ログレベル等）をプロパティ経由で取得。値検証（KABUSYS_ENV, LOG_LEVEL）を実施。

- AI（LLM）関連
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）を追加。
    - raw_news / news_symbols を集約し銘柄別に記事をまとめ、gpt-4o-mini の JSON mode を用いて銘柄ごとのセンチメントを取得。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数と文字数を制限（トリム）。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンス検証（JSON 抽出・results 配列・code/score の型検査・既知コードのみ採用）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的（DELETE → INSERT）に書き込み。
    - テスト容易性のため API 呼び出し箇所をパッチ差し替え可能（_call_openai_api をモック可能）。
    - api_key を引数で注入可能（環境変数 OPENAI_API_KEY も使用可能）。

  - 市場レジーム判定モジュール（kabusys.ai.regime_detector）を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を決定。
    - マクロキーワードでニュースをフィルタし、gpt-4o-mini により -1.0〜1.0 のスコアを取得（JSON モード）。API の再試行とフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - レジームスコアを計算して market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策: datetime.today() を参照せず、prices_daily クエリも target_date 未満のデータのみ参照。

- データ基盤（Data）
  - ETL パイプラインの公開インターフェース（kabusys.data.etl）と ETLResult データクラス（kabusys.data.pipeline）を追加。
    - ETLResult に取得件数 / 保存件数 / 品質チェック結果 / エラー概要を格納し、簡易的な to_dict 出力を提供。
  - pipeline モジュール:
    - 差分取得、バックフィル、品質チェックの設計（DataPlatform.md に準拠する想定）。
    - DuckDB を用いたテーブル存在確認や最大日付取得ユーティリティを実装（_table_exists, _get_max_date 等）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）を追加。
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日判定 API を提供。
    - DB 登録値がない場合の曜日ベースフォールバックや、DB 値優先の一貫した挙動を担保。
    - 最大探索日数・先読み・バックフィル・健全性チェック等の安全策を実装。

- リサーチ（研究）機能
  - kabusys.research パッケージを追加（factor_research, feature_exploration）。
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR、ATR 比率、出来高等）、Value（PER・ROE）を DuckDB 上で計算する関数を実装。
    - 欠損データやデータ不足時に None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - スピアマン IC の計算（ランクの平均化で ties 対応）、中央値・分散等の統計量を標準ライブラリのみで実装。

### 変更 (Changed)
- なし（初期リリースのため該当なし）

### 修正 (Fixed)
- なし（初期リリースのため該当なし）

### 注意点 / 既知の問題 (Known issues / Notes)
- 一部参照先モジュールについて
  - calendar_management / pipeline 等は kabusys.data.jquants_client（jq）を利用する実装になっているが、提示コードでは jquants_client の実装は含まれていない（別モジュールとして提供される前提）。実行環境では jquants_client の提供が必要。
  - パッケージの公開 API（src/kabusys/__init__.py）の __all__ に "strategy", "execution", "monitoring" が含まれているが、今回提供されたスニペットにはこれらの実装が無い。今後追加予定。

- 実装上の問題（要修正）
  - kabusys.data.pipeline モジュール末尾付近に実装途切れ・明らかなタイポ（`return date.fro` のような不完全な戻り）が見られるため、そのままでは実行時に例外が発生する可能性がある。リリース前に該当行の修正が必要。
  - DuckDB への executemany やリストバインドの挙動が DB バージョン依存であるため、実装内に注意書き（空リストの扱いなど）を含むが、実行環境の DuckDB バージョン差異による影響を確認してください。

- 動作上の留意点
  - LLM 呼び出しは OpenAI SDK（OpenAI クライアント）を想定。API キーは引数で注入可能だが、未設定時は OPENAI_API_KEY 環境変数が必須（未設定時は ValueError を送出）。
  - LLM レスポンスの堅牢化処理を多数実装しているが、期待する JSON スキーマでないレスポンスはスキップされる（フェイルセーフ設計）。
  - 日付/時間の取り扱いはルックアヘッドバイアスを避けるため datetime.today() / date.today() を多くの処理で利用せず、すべて呼び出し元から与えられる target_date に依存する設計。

### セキュリティ (Security)
- 設定に機密情報（API キー等）を使用する想定のため、環境変数経由での設定を推奨。自動 .env ロードはテスト用に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- OpenAI API への呼び出しは外部サービス依存のため、キー管理・利用規約に注意してください。

---

参考: 主に次の機能を中心に実装が行われています。
- 環境設定（.env 自動読み込み、Settings）
- DuckDB を用いたデータパイプライン（ETL/カレンダー/品質チェックの枠組み）
- LLM を用いたニュース・マクロ評価（ニュース NLP、レジーム判定）
- 研究用ファクター計算・統計ユーティリティ

改善・バグ修正・ドキュメント補完が必要な箇所を逐次反映していく予定です。変更履歴は今後のリリースごとに更新してください。