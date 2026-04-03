# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- メジャーリリース方針: 新規リリースごとに主要な機能追加や API をここに記載します。  
- 日付はリリース日を表します。

## [0.1.0] - 2026-04-03

初回公開リリース。

### 追加 (Added)
- パッケージの基礎
  - パッケージ初期化と公開 API を追加。バージョン情報と主要サブパッケージをエクスポート (src/kabusys/__init__.py)。

- 環境設定管理
  - .env または環境変数から設定を読み込む Settings クラスを実装（src/kabusys/config.py）。
  - 自動 .env 読み込み機能を追加。優先順位は OS 環境変数 > .env.local > .env。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの強化:
    - 空行・コメント行対応。
    - export プレフィックス対応。
    - シングル/ダブルクォート内のエスケープ処理対応。
    - インラインコメント処理（クォートなしの場合は '#' の直前が空白/タブのときコメントとして扱う）。
  - 必須環境変数取得用の _require と、環境値の妥当性検証（KABUSYS_ENV, LOG_LEVEL）を追加。
  - デフォルト値や Path 型変換などのユーティリティを提供（DuckDB/SQLite/監視用ファイルパス等）。

- ニュース NLP（AI）機能
  - ニュースに基づく銘柄毎センチメントスコアリング機能を実装（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算（calc_news_window）。
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約し、最大記事数 / 最大文字数でトリム。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ送信（最大 20 銘柄/チャンク）。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフのリトライロジック。
    - レスポンスの厳密なバリデーションと数値変換、±1 にクリップしたスコアを ai_scores テーブルへ冪等的に書き込み。
    - DuckDB の executemany の制約（空リスト不可）を考慮した実装。
    - テスト容易性のため API 呼び出し部分はパッチ差し替え可能な実装。

  - 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次で regime を判定（bull/neutral/bear）。
    - マクロキーワードフィルタによるニュース抽出、OpenAI 呼び出し、リトライ/フォールバック（失敗時は macro_sentiment=0.0）を実装。
    - DB（market_regime）へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策: target_date を明示的に受け取り、内部で date.today() を参照しない設計。

- 研究（Research）機能
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility & Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: PER、ROE（raw_financials から最新の財務データを取得して計算）。
    - DuckDB ベースの SQL 実装で、(date, code) をキーとする辞書リストを返却。
  - 特徴量探索ユーティリティを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（複数ホライズン対応: デフォルト [1,5,21]）。
    - IC（Information Coefficient、Spearman の ρ）計算。
    - ランク変換ユーティリティ（同順位は平均ランク）。
    - ファクターの統計サマリー（count/mean/std/min/max/median）。
  - research パッケージのエクスポート整理（src/kabusys/research/__init__.py）。

- データプラットフォーム機能
  - マーケットカレンダー管理モジュール（src/kabusys/data/calendar_management.py）。
    - 営業日判定（is_trading_day）、翌営業日/前営業日取得、期間内営業日取得、SQ 日判定を実装。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（平日を営業日と扱う）。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装し、J-Quants から差分取得→冪等保存（jq.fetch_market_calendar / jq.save_market_calendar を使用）。
    - 最大探索日数制限や健全性チェック、バックフィル戦略を組み込み。
  - ETL パイプラインと結果型（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - 差分取得・保存・品質チェックを行う ETL のインターフェース設計。
    - ETLResult データクラスで取得件数 / 保存件数 / 品質問題 / エラーを集約。
    - jquants_client と quality モジュールへの役割分担を前提とした設計。

- 互換性・テスト性のための工夫
  - OpenAI API 呼び出し部分は関数化してテスト時に unittest.mock.patch で差し替え可能。
  - DuckDB のバージョン差異（executemany の空リスト問題等）に配慮した実装。
  - ルックアヘッドバイアス回避のため、すべての主要処理で target_date を明示的に受け取り、内部で現在時刻を参照しない方針を採用。

### 注意事項 / 既知の挙動 (Notes)
- OpenAI API キー:
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数を受け取ります。api_key を与えない場合は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出します。
- .env 自動読み込み:
  - プロジェクトルートは __file__ から上位ディレクトリを探索して .git または pyproject.toml を基準に判定します。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- 環境変数の保護:
  - 自動ロード時は既存の OS 環境変数を protected として扱い、.env の上書きを回避する設計です（ただし .env.local は override=True で読み込み順により上書きされます）。
- DuckDB 依存挙動:
  - executemany に空リストを渡すと失敗するバージョンがあるため、空チェックを行ってから executemany を呼び出しています。
- フォールバックポリシー:
  - LLM 呼び出しや外部 API の失敗時はフェイルセーフとしてスコアに中立値（0.0 など）を採用し処理を継続する設計です（例: macro_sentiment=0.0）。
- KABUSYS_ENV と LOG_LEVEL:
  - Settings で受け付ける値はそれぞれ限定されています。無効な値を設定すると ValueError が発生します。
    - KABUSYS_ENV: development, paper_trading, live
    - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL

### 変更 (Changed)
- （初回リリースのためなし）

### 修正 (Fixed)
- （初回リリースのためなし）

### 非推奨 (Deprecated)
- （初回リリースのためなし）

### 削除 (Removed)
- （初回リリースのためなし）

### セキュリティ (Security)
- （初回リリースのため特記事項なし）

---

今後の予定: API の拡張（追加ログ出力、メトリクス連携、より細かい品質チェックルール）、より堅牢なテストカバレッジ、およびドキュメントの充実を想定しています。必要であれば、この CHANGELOG により詳細なファイル単位の変更や実装理由を追記します。