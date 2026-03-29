# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
このファイルは、リポジトリ内のコードから機能・設計方針・重要な実装意図を推測して作成した初期の変更履歴です。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回リリース。日本株の研究・データ基盤・AIスコアリング・市場レジーム判定を一通り実装した最小実用版。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージの公開 API（__all__）を整備（data, strategy, execution, monitoring などを想定してのエクスポート）。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env/.env.local を自動でプロジェクトルートから読み込む自動ロード機能を追加。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを実装:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォートなしは '#' の直前が空白またはタブの場合にコメントとして扱う）
    - ファイル読み込み失敗時に警告を発する（warnings.warn）
  - 環境変数取得ユーティリティ Settings を実装:
    - J-Quants, kabuステーション, Slack, DB パス等のプロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）
    - env（KABUSYS_ENV）と log_level（LOG_LEVEL）に対する入力検証（有効値の限定）
    - is_live / is_paper / is_dev のヘルパーを提供
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング（score_news）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを生成
    - バッチサイズ、記事数上限、文字数トリム等のトークン肥大化対策を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - JSON Mode を利用し厳密な JSON 応答を期待、レスポンス検証ロジックを実装（_validate_and_extract）
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ（最大リトライ回数の設定）
    - API失敗時はそのチャンクをスキップするフェイルセーフ。部分成功時は書き込み対象コードのみを置換（DELETE → INSERT）して既存データ保護
    - ニュース収集ウィンドウの計算ロジック（JST 前日15:00～当日08:30 相当の UTC 範囲）を提供（calc_news_window）
    - 単体テストを容易にするための差し替えポイントを用意（_call_openai_api を mock 可能）
  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - レジーム合成の閾値やスケールが定義済み（_MA_WEIGHT, _MACRO_WEIGHT, しきい値等）
    - マクロニュース抽出のキーワードリストを実装（_MACRO_KEYWORDS）
    - OpenAI 呼び出しに対する堅牢なリトライ／エラーハンドリングを実装し、API 失敗時は macro_sentiment=0.0 にフォールバック
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施
- 研究（Research）モジュール (src/kabusys/research)
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）などの計算関数を追加
    - DuckDB の SQL ウィンドウ関数を活用した実装
    - データ不足時の null ハンドリング（行数不足で None を返す等）
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（複数ホライズンの LEAD を利用）、IC（Spearman）計算、ランク変換、ファクター統計サマリーを実装
    - 外部依存を避け標準ライブラリと DuckDB のみで実装
  - research パッケージの __all__ を整備して主要関数を公開
- データ基盤（Data）モジュール (src/kabusys/data)
  - カレンダー管理（calendar_management）
    - market_calendar を参照して営業日判定（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供
    - カレンダー未取得時の曜日ベースのフォールバック（週末は非営業日）
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装し J-Quants から差分取得して保存（バックフィル・健全性チェックを含む）
    - 最大探索日数等の安全措置を備える（_MAX_SEARCH_DAYS 等）
  - ETL パイプライン（pipeline）
    - ETLResult dataclass を追加し、ETL 実行結果・品質問題・エラーの集約を提供
    - 差分取得ロジック、バックフィル方針、品質チェックの考え方を実装（jquants_client と quality モジュールを利用）
  - ETL 用の公開インターフェース（etl.py）で ETLResult を再エクスポート
  - jquants_client によるデータ取得/保存の抽象化を利用する設計（モジュール参照を用意）
- ロギング・設計方針
  - 各モジュールで詳細な logger 呼び出しを配置（info/debug/warning/exception）
  - ルックアヘッドバイアスを避けるため、datetime.today()/date.today() をベース処理で直接参照しない設計方針を採用（target_date を引数で受ける形）
- テストしやすさ
  - OpenAI 呼び出しや時間依存処理に差し替え可能なポイント（関数）を設け、ユニットテストでのモックを想定

### 変更 (Changed)
- （初回リリースのため既存の変更履歴はなし。ただし、設計上以下の点を明記）
  - DuckDB に対する executemany の空リストバインドが不安定なバージョンを考慮し、空リストの場合は実行をスキップする保護を追加（news_nlp, pipeline の DB 書き込み周り）
  - OpenAI SDK の例外バリアント（status_code の有無など）を安全に扱うため getattr を使用する等の互換性処理を導入

### 修正 (Fixed)
- （初回リリースのため過去のバグ修正履歴はなし。ただし実装上のフェイルセーフ）
  - OpenAI API のエラー時は例外伝播させずフォールバック値（0.0）を用いることで上位処理の継続を保証（score_news, score_regime の一部挙動）
  - DB 書き込み失敗時に ROLLBACK を試み、失敗すればログに警告を出す保護を追加

### 既知の制限 / 注意事項 (Known issues / Notes)
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出する箇所がある。
- JSON mode を期待するため、LLM の応答フォーマットが崩れると該当チャンク/記事はスキップされる。
- DuckDB の日付型や executemany の振る舞いは利用する DuckDB バージョンに依存するため、本番環境では互換性確認が必要。
- calendar_update_job は J-Quants クライアント（jquants_client.fetch_market_calendar / save_market_calendar）に依存。API エラー時は 0 を返す（例外を上位に投げない）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に探索するため、配布後や特殊なインストール形態では自動読み込みがスキップされることがある（その場合は環境変数を直接設定する必要あり）。

### セキュリティ (Security)
- 環境変数の自動上書きを防止するため、OS 環境変数を protected set として扱い .env ファイルの上書きを制御。
- 機密情報（API キー等）は Settings を通じて取得するが、ログにキーの値を出力しない実装が想定される（コード上では明示的に出力していない）。

---

作成した CHANGELOG はコードから推測してまとめたものです。実際のコミット単位やリリース日・追加された小さなユーティリティなどは、実際の VCS 履歴に基づいて調整してください。必要であれば、各モジュールごとの詳細な変更点や例示（環境変数一覧、API の呼び出し例、DB スキーマ想定など）を追加で展開できます。