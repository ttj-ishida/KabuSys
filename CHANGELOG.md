# Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠して記載します。

## [0.1.0] - 初回リリース (未リリース日付)
初期公開リリース。以下の主要機能・モジュールを実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化: kabusys.__version__ = "0.1.0" を設定し、公開 API として data/strategy/execution/monitoring をエクスポート。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を追加。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索）。
  - よくある .env 形式（export プレフィックス、シングル/ダブルクォート、インラインコメントなど）に対応する堅牢なパーサを実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスを提供し、アプリケーション構成値（J-Quants / kabuステーション / Slack / データベースパス / 環境モード / ログレベル等）をプロパティで取得可能に。
  - 必須環境変数読み取り時に未設定なら ValueError を送出する `_require` を実装。
- AI モジュール (kabusys.ai)
  - ニュースNLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む `score_news` を実装。
    - ニュース収集ウィンドウ計算 `calc_news_window`（JST 前日 15:00 ～ 当日 08:30 → UTC に変換）を提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり最大記事数・文字数制限（トリム）を実装しトークン膨張に対応。
    - OpenAI 呼び出しは JSON mode を利用し、レスポンスのバリデーション処理を実装（結果フォーマットの厳密チェック、数値変換、クリッピング）。
    - 429/ネットワーク/タイムアウト/5xx に対するエクスポネンシャルバックオフによるリトライ、フェイルセーフでのスキップ（部分成功を許容）を実装。
    - テスト容易性のため OpenAI 呼び出し用関数を patch で差し替え可能に設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する `score_regime` を実装。
    - MA200 比率計算、マクロニュース抽出（キーワードフィルタリング）、OpenAI でのマクロセンチメント評価、スコア合成、冪等的な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - API エラー時のフェイルセーフ: macro_sentiment を 0.0 として処理を継続。
    - OpenAI 呼び出しに対するリトライ＆バックオフ、JSON パースの耐性（パース失敗時は 0.0 を返す）を実装。
- データモジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を基に営業日判定ロジックを提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録を優先し、未登録日は曜日ベース（週末）でフォールバックする一貫した挙動を実装。
    - 最大探索日数制限や健全性チェック、JPX カレンダー差分取得ジョブ `calendar_update_job` を実装（J-Quants クライアント呼び出し、バックフィル挙動、例外ハンドリング）。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを公開し、ETL の取得/保存件数や品質チェック結果・エラー情報を集約可能に。
    - テーブル存在チェック、最大日付取得ユーティリティ等の内部ヘルパを実装。
    - 差分更新・バックフィルの方針を組み込む設計（詳細はモジュール docstring）。
- リサーチ（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン・MA200 乖離）、ボラティリティ（20日 ATR）、流動性指標（20日平均売買代金・出来高比率）、バリューファクター（PER, ROE）を DuckDB 上で計算する関数群を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB のウィンドウ関数を活用し、データ不足時は None を返すなど堅牢な実装。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 `calc_forward_returns`（horizons のバリデーション、効率的な一括クエリ取得）。
    - IC（Information Coefficient）計算 `calc_ic`（スピアマン ρ のランク相関実装、必要件数チェック）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸めによる ties 対策）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median の出力）。
- その他
  - 各モジュールで DuckDB 接続を受け取り外部副作用を最小化する設計を採用。
  - ほとんどの処理で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取ることでルックアヘッドバイアスを回避する設計方針を徹底。

### 変更 (Changed)
- （新規リリースのため該当なし）

### 修正 (Fixed)
- （新規リリースのため該当なし）

### 非推奨 (Deprecated)
- （新規リリースのため該当なし）

### 削除 (Removed)
- （新規リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーや各種シークレットは環境変数経由で取得し、未設定時は明示的にエラーを出す仕様。自動 .env ロードを明示的に無効化する環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。

---

注:
- OpenAI 関連の機能は外部 API に依存します。API 失敗時は概ねフェイルセーフ（スコアを 0.0 とする、処理をスキップして残りを継続など）で動作するよう設計されていますが、API 利用料やレート制限、モデルの挙動に注意してください。
- DuckDB のバージョンや接続先スキーマによっては executemany の制約（空リスト渡し不可など）に注意した実装がなされています。運用時は DuckDB の互換性を確認してください。