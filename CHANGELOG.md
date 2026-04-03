# Keep a Changelog — kabusys

すべての変更は [Keep a Changelog](https://keep-a-changelog.com/ja/1.0.0/) に準拠して記載しています。  
このファイルはコードベース（src/kabusys/*）の内容から推測して作成した初期の変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

初回リリース（推定）。以下の主要機能とモジュールを追加しました。

### 追加 (Added)
- パッケージ全体
  - kabusys パッケージ v0.1.0 を追加。公開 API として data, research, ai, monitoring, strategy, execution 等のモジュール群を想定。
  - パッケージバージョン: __version__ = "0.1.0"。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準に判定（配布後の動作を考慮）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは以下をサポート:
    - export KEY=val 形式、
    - シングル/ダブルクォート内でのバックスラッシュエスケープ、
    - クォートなしでのインラインコメント扱い（直前がスペース/タブの場合）。
  - Settings クラスを提供し、プロパティ経由で設定値を取得:
    - J-Quants / kabuステーション / LINE Messaging / DB パス（DuckDB/SQLite）/監視用設定（PID ファイル、kill flag、CPU/メモリ/ディスク閾値）/環境（development/paper_trading/live）/ログレベルなど。
    - 必須環境変数未設定時は ValueError を送出する _require を採用。
    - 環境値検証（KABUSYS_ENV・LOG_LEVEL の許容値チェック）。

- AI: ニュース NLP & レジーム判定 (src/kabusys/ai/)
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントスコアを算出。
    - バッチ処理（最大 20 銘柄/バッチ）・1銘柄あたり記事数トリム（最大 10記事、最大 3000文字）を実装。
    - 429 / ネットワーク切断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフとリトライ。
    - レスポンス検証ロジック（JSON 抽出、results 配列、code/score 検証、スコアを ±1.0 にクリップ）。
    - 成功分のみ ai_scores テーブルに対して部分的に置換（DELETE → INSERT）し、部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
    - タイムウィンドウ計算: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ実施）。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュース抽出はマクロキーワードを用いて raw_news からタイトルを取得、OpenAI（gpt-4o-mini）に投げて JSON 形式で macro_sentiment を取得。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 にフォールバック（例外を上げない）。
    - リトライ/バックオフ戦略、レスポンスパースの堅牢化、最大記事数制限を実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込みエラー時は ROLLBACK を試行し例外を伝播。

- データプラットフォーム (src/kabusys/data/)
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar を基にした営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがある場合は DB 値を優先、未登録日の場合は曜日（平日/週末）フォールバックを行い、一貫性を確保。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。
    - calendar_update_job により J-Quants API からの差分取得・バックフィル（直近 _BACKFILL_DAYS の再取得）・健全性チェック（将来日付の過大チェック）を実装。jquants_client を介して fetch/save を行う。
  - pipeline / etl（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を追加し、ETL 実行結果の構造化（取得数・保存数・品質チェック結果・エラー一覧等）を提供。
    - 差分更新、backfill、品質チェック呼び出しの設計に沿った ETL パイプラインの基盤（jquants_client / quality モジュールと連携する想定）。
    - DuckDB のテーブル存在確認ユーティリティ _table_exists / _get_max_date などを実装。
    - DuckDB の executemany に関する互換性（空リスト不可）を考慮した実装。

- リサーチ（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）等のファクター計算関数を追加。
    - DuckDB を使った SQL＋ウィンドウ関数による効率的な実装。データ不足時は None を返す設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算、ランク変換、ファクター統計サマリー（factor_summary）を追加。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で実装。
  - research パッケージの __all__ で主要関数を再エクスポート。

### 変更 (Changed)
- （初回リリースにつき無し）

### 修正 (Fixed)
- （初回リリースにつき無し）

### 注意事項（重要な実装/運用上のポイント）
- OpenAI API
  - 多くの AI 機能は OpenAI SDK（OpenAI クライアント）に依存します。api_key は各関数呼び出しの api_key 引数または環境変数 OPENAI_API_KEY で指定する必要があります。未設定の場合は ValueError を送出します。
  - 使用モデルは gpt-4o-mini、JSON mode（response_format）を想定して設計されています。レスポンスのバリデーションや JSON 抽出ロジックを備えていますが、実運用時はモデル出力の差異に注意してください。
- データベース（DuckDB）
  - モジュールは DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）の存在を前提とします。適切なスキーマ準備が必要です。
  - DuckDB executemany に対する空リスト制約に配慮した実装（空の params は送らない）をしています。
- 自動 .env ロード
  - プロジェクトルート検出は .git または pyproject.toml に依存します。配布先で自動読み込みを制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
  - .env の読み込みでは OS 環境変数を保護するため protected set を使用し、.env.local による上書きをサポートします。
- ルックアヘッドバイアス対策
  - AI 評価やファクター計算等で datetime.today() / date.today() を直接参照せず、target_date を明示的に渡す設計になっています（テスト・解析の再現性確保のため）。
- フェイルセーフ
  - API 呼び出し失敗時は即時例外を投げるのではなく、安全なデフォルト（スコア 0.0 や処理スキップ）で継続する設計を採用しています。ただし DB 書き込み時など致命的なエラーは上位へ伝播します。
- 依存と互換性
  - Python の型注釈に |（ユニオン）を使用しているため、Python 3.10 以上を想定しています。
  - OpenAI SDK と DuckDB が必須の実行依存です。

### 既知の制限 / 今後の改善候補
- jquants_client, quality モジュール等は外部 API との接続点であり、実装/設定に応じた依存管理が必要。
- news_nlp / regime_detector のプロンプトやモデル、バッチサイズ、重み付けなどは将来的にパラメータ化すると運用が容易になります。
- ai モジュールのレスポンス検証は堅牢化を図っていますが、モデル出力の予期せぬ形式に対するさらなるロギング/監査が有用です。

---

（上記は提示されたソースコードから推測して作成した CHANGELOG です。実際のリリースノートはリリース時のコミット履歴、変更内容、公開日付に合わせて更新してください。）