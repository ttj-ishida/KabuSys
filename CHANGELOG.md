# CHANGELOG

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

最新の変更は上に記載します。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システムの基本モジュール群を実装・公開しました。主な追加点を機能ごとに整理します。

### 追加（Added）
- パッケージ基盤
  - パッケージ初期化情報を導入（kabusys.__version__ = 0.1.0）。
  - パッケージの公開 API として data / strategy / execution / monitoring を __all__ に追加。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を基準に探索）。
  - .env ファイルの柔軟なパース：
    - コメント・空行・export プレフィックスに対応。
    - シングル/ダブルクォート内のエスケープ対応。
    - インラインコメントの取り扱い（クォート有無での扱いの違い）。
  - OS 環境変数の保護（protected set）を実装し、.env の上書き制御を提供。
  - 自動ロード制御のため KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須設定取得のユーティリティ _require と Settings クラスを実装：
    - J-Quants / kabu / Slack / DB パス等のプロパティを提供。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）。
    - is_live / is_paper / is_dev の補助プロパティ。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）:
    - market_calendar テーブルを用いた営業日判定ロジックを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days などのユーティリティを実装。
    - DB の有無や欠落値時の曜日ベースのフォールバック、最大探索日数の安全策を導入。
    - calendar_update_job: J-Quants クライアント経由で差分取得し冪等的に保存する夜間バッチ処理を実装。バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー集約など）。
    - 差分更新、バックフィル、品質チェックのための設計を文書化。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- AI（kabusys.ai）
  - ニュース NLP（news_nlp）:
    - raw_news と news_symbols を元に記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出・ai_scores に書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC naive datetime に変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事数上限および文字数トリムによるトークン肥大化対策を実装。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他はスキップして継続（フェイルセーフ）。
    - レスポンス検証ロジックを実装（JSON 抽出、results リストの検証、未知コードの無視、数値チェック、スコアクリップ）。
    - テスト容易性のために OpenAI 呼び出しを差し替え可能なポイント（_call_openai_api）を設ける。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント判定、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 障害時は macro_sentiment=0.0 にフォールバックして継続（フェイルセーフ）。
    - LLM 呼び出しのリトライと 5xx 判別ロジックを実装。
    - ルックアヘッドバイアス対策（内部で date.today() を直接参照しない、DB クエリは target_date 未満の排他条件など）を採用。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）:
    - モメンタム（1M/3M/6M）、ma200 乖離、ATR（20日）、流動性（20日平均売買代金、出来高比）などを DuckDB SQL で実装。
    - raw_financials を用いたバリューファクター（PER, ROE）計算を実装。
    - データ不足時の None ハンドリング・効率的なスキャン範囲（buffer）を備えた実装。
  - 特徴量解析（feature_exploration）:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic: スピアマンのランク相関）、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas など外部重いライブラリに依存せず標準ライブラリと DuckDB で実装。
  - data.stats の zscore_normalize を re-export。

### 変更（Changed）
- ドキュメント化・設計上の方針を各モジュールの docstring に反映：
  - ルックアヘッドバイアス防止方針の明確化（core ロジックが datetime.today()/date.today() を参照しない）。
  - DuckDB のバージョン差異（executemany の空リスト制約等）への対処を実装。

### 修正（Fixed）
- 初期リリースのため、コードベースでの既知の軽微なログ/警告ハンドリングやロールバック失敗時の警告ログ出力を追加して耐障害性を向上。

### セキュリティ（Security）
- 環境変数読み込みで OS 環境変数を保護する機構を導入（.env による上書きから保護）。
- OpenAI API キー等の必須変数の未設定時に明確なエラーを返すように実装。

### 既知の制限（Known issues / Notes）
- OpenAI クライアントは openai パッケージに依存しており、実行には有効な OPENAI_API_KEY が必要。テスト用に _call_openai_api をモックすることが想定されている。
- news_nlp/regime_detector の LLM 呼び出しは JSON mode の応答に依存するため、LLM 側の応答仕様変化に対しては保守が必要。
- 一部の関数は DuckDB の具体的なバインド動作や日付型の戻り値に依存しており、環境差異に注意が必要。

---

貢献・バグ報告は issue を立ててください。次回リリースでは以下を検討しています：監視/発注系の実装（execution / monitoring の詳細実装）、より詳細な品質チェックルール、テストカバレッジの拡充。