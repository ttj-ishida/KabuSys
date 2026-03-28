# Changelog

すべての重要な変更をこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - 公開モジュール群: data, research, ai, execution, strategy, monitoring（__all__ により想定される構成を提示）。

- 環境設定および自動 .env 読み込み (src/kabusys/config.py)
  - .env / .env.local ファイルをプロジェクトルート（.git または pyproject.toml を探す）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを明示的に無効化可能。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - OS 環境変数を保護する protected set を用いた読み込み順序: OS 環境 > .env.local > .env。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 /ログレベル等の設定プロパティを公開。未設定時の必須キー取得時には明確な ValueError を発生。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ処理（最大20銘柄/回）、JSON Mode 応答の検証、スコア ±1.0 クリッピング。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ再試行。
    - レスポンスパース失敗やAPI失敗は個別チャンクをスキップして全体処理を継続（フェイルセーフ）。
    - DuckDB の制約（executemany に空リスト不可）を考慮した部分書換ロジック（DELETE → INSERT）。
    - テスト用に _call_openai_api を patch して差し替え可能な設計。
    - タイムウィンドウ定義: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロセンチメントはニュースタイトルを抽出して LLM（gpt-4o-mini）で JSON レスポンスを期待。
    - 再試行ロジック、API失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - レジーム結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - lookahead バイアス回避の設計（date 未満のデータを参照、datetime.today() を直接参照しない）。

- データプラットフォーム (src/kabusys/data/)
  - ETL パイプライン (data.pipeline, data.etl)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー等を保持）。
    - 差分取得・バックフィル・品質チェックを想定した設計。デフォルトの backfill_days や最小データ日付定義あり。
  - マーケットカレンダー管理 (data.calendar_management)
    - market_calendar テーブルを基に営業日判定・次/前営業日検索・期間内営業日列挙を提供。
    - カレンダーデータ未取得時は曜日ベース（土日非営業）でフォールバック。
    - JPX カレンダー夜間更新ジョブ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存）。
    - next_trading_day / prev_trading_day は _MAX_SEARCH_DAYS により無限ループを防止。
  - jquants_client を想定した fetch/save の利用に準備（jq モジュールへの依存）。

- 研究 / ファクター算出 (src/kabusys/research/)
  - factor_research: calc_momentum / calc_value / calc_volatility の実装
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - ボラティリティ: 20日 ATR、ATR比率、20日平均売買代金、出来高比率。
    - バリュー: PER（EPS が 0 または欠損なら None）、ROE（raw_financials から最新を参照）。
    - DuckDB を用いた SQL 中心の処理、営業日ベースの窓計算、結果は (date, code) キーの辞書リストで返却。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装
    - 将来リターンの一括取得（複数 horizon 対応、horizons の検証あり）。
    - スピアマンランク相関（IC）計算、ランクの扱い（同順位は平均ランク）。
    - 統計サマリー（count/mean/std/min/max/median）を純粋標準ライブラリで実装。
  - research パッケージから主要ユーティリティを再公開。

### 変更 (Changed)
- 設計方針文書化
  - 各モジュールで「ルックアヘッドバイアス防止」「フェイルセーフ」「DuckDB 互換性」などの設計判断を明文化して実装に反映。

### 修正 (Fixed) / 耐障害性の向上
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ処理、行内コメントの扱い、export プレフィックス対応などをサポートし、不正行は無視する。
  - .env ファイルの読み込み失敗時には警告を出して処理継続するようにして、致命的エラーにならないようにした。
- OpenAI API 呼び出しまわりの耐障害性
  - 429 / 接続断 / タイムアウト / 5xx を対象とした再試行（指数バックオフ）を実装。非 5xx の APIError は再試行せずフォールバックする。
  - レスポンスパース失敗・不正レスポンス時は警告ログを出し、0.0 や空辞書でフォールバックして処理継続。
- DuckDB 互換性対応
  - executemany に空リストを渡せないバージョンを考慮し、書込み前に params が空でないかをチェック。
  - market_calendar / ai_scores 等の更新を部分的に行い、部分失敗時にも既存データを保護する処理にした。
- テスト容易性
  - news_nlp と regime_detector の OpenAI 呼び出しを内部関数化しており、ユニットテストで差し替え（mock.patch）可能。

### 注意事項 (Notes)
- OpenAI API キー
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定だと ValueError を送出する。
- 環境変数必須項目
  - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等は Settings のプロパティで必須となっているため、実行前に .env または環境変数で設定してください。
- フェイルセーフ設計
  - AI API の失敗や記事不足時は 0.0（中立）やスコア未取得扱いで処理を継続するため、AI 部分の不調が全体処理を停止させない設計になっています。ただしその場合はログに WARN/INFO が出力されます。
- 外部依存
  - 実装は標準ライブラリと duckdb、openai SDK を前提としています。研究モジュールは pandas 等を使用しない純実装です。
- 互換性
  - DuckDB のバージョン依存の挙動（executemany の空リスト等）を考慮していますが、利用環境の DuckDB バージョンにより動作差分があり得ます。

---

今後のリリースでは以下のような点を検討しています（例）:
- ai_score と sentiment_score の分離・拡張
- strategy / execution / monitoring の具体的実装とテストカバレッジ拡充
- J-Quants / kabu API 周りのエラーハンドリング強化とリトライ戦略のパラメタ化

（初回リリース: kabusys 0.1.0）