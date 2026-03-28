# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルには、パッケージ初期リリース（v0.1.0）で導入された機能・仕様・実装上の重要な設計判断を記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買システム "KabuSys" のコアライブラリ群を追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: `src/kabusys/__init__.py` にバージョン `0.1.0` と公開サブモジュール一覧を定義。
- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロードの優先順: OS環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード抑止機能を提供（テスト向け）。
  - .git または pyproject.toml を基準にプロジェクトルートを探索してファイルをロード（CWD 非依存）。
  - .env のパース機能を強化:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの取り扱い。
  - Settings クラス提供: 環境変数からアプリ設定を取得するプロパティ群（J-Quants、kabu API、Slack、DBパス、実行環境・ログレベル判定等）。
    - 必須項目未設定時は明示的なエラー（ValueError）を投げる `_require` を採用。
- AI（自然言語処理）モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - raw_news / news_symbols を集約して銘柄ごとのテキストを生成し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを算出。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数・文字数の制限（トリム）を実装。
    - レスポンス検証・スコアの ±1.0 クリップ、部分成功時は既存スコア保護のため対象コードのみ置換（DELETE → INSERT）。
    - OpenAI 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンスパース失敗等はフェイルセーフでスキップして継続。
  - 市場レジーム判定 (`regime_detector.score_regime`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を決定。
    - マクロニュースは `news_nlp.calc_news_window` に基づくウィンドウ内でキーワード検索し、OpenAI により JSON 応答でセンチメントを取得。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。
  - テスト容易性を考慮し、OpenAI 呼び出しはモジュール内部で差し替え可能に設計（関数を patch できる）。
- リサーチ（因子・特徴量解析）モジュール (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算する `calc_momentum`。
    - バラティリティ/流動性: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算する `calc_volatility`。
    - バリュー: 最新の raw_financials から PER/ROE を計算する `calc_value`。
    - DuckDB のウィンドウ関数を活用し、営業日ベースの窓を考慮した実装。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算: `calc_forward_returns`（デフォルト horizons=[1,5,21]）。
    - IC（情報係数）計算: スピアマンランク相関を求める `calc_ic`。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - 標準ライブラリのみで完結する実装（pandas 等に依存しない）。
- データプラットフォーム周り (`kabusys.data`)
  - マーケットカレンダー管理 (`data.calendar_management`)
    - JPX カレンダーの夜間差分更新バッチ `calendar_update_job`（J-Quants から差分取得し保存）。
    - 営業日判定 API: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック（週末を非営業日と扱う）。
    - 最大探索日数制限やバックフィル、健全性チェックを実装。
  - ETL パイプライン (`data.pipeline`)
    - ETL の設計に基づく差分取得 → 保存 → 品質チェックフローを実装する基盤。
    - ETL 実行結果を表す dataclass `ETLResult` を提供（品質問題一覧・エラー要約を含む）。
    - テーブル存在チェック・最大日付取得ユーティリティ等を提供。
  - ETL 公開インターフェースとして `data.etl` で `ETLResult` を再エクスポート。
  - J-Quants クライアントは `kabusys.data.jquants_client` 経由で利用（カレンダー fetch/save 呼び出しを想定）。
- DuckDB 互換性考慮
  - DuckDB 0.10 の executemany における空リストバインドの問題を回避する条件分岐を導入（空パラメータのときは実行をスキップ）。
- その他ユーティリティ
  - タイムウィンドウ計算（ニュースウィンドウは JST ベースで計算し、DB 比較用に UTC-naive datetime を返す）。
  - ログレベル/環境判定用の検証（有効な env 値や LOG_LEVEL の検査）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- API 応答の JSON パース時に前後の余計なテキストが混入するケースを想定して、最外の {} を抽出して復元するフォールバックを実装（news_nlp）。
- OpenAI API 呼び出し失敗時の挙動を明確化:
  - 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。
  - 非 5xx の API エラーやパース失敗はログに記録してフェイルセーフにより 0.0 や空スコアで継続。
- DuckDB の日付値取り扱いに関する変換ユーティリティを追加し、型の揺らぎに対応。

### セキュリティ (Security)
- 機密情報（OpenAI API キー、Slack トークン、kabu API パスワード等）は Settings 経由で環境変数から取得。必須値未設定時は起動時に明示的エラーを発生させることで設定漏れを防止。
- .env 読み込み時に OS 環境変数を保護する機能を実装（既存の OS 環境変数はデフォルトで上書かれない）。

### 既知の制約・注意点 (Notes)
- 全モジュールでルックアヘッドバイアスを避けるため、内部で datetime.today() / date.today() を参照しない設計となっている（呼び出し側が target_date を渡す）。
- OpenAI 呼び出しは外部ネットワークに依存するため、テスト時は各モジュールの _call_openai_api をモックすることを想定。
- 一部モジュール（strategy / execution / monitoring）は __all__ に含まれているが、このリリースでの実装は本CHANGELOG対象のファイル群に限定されます。

### 将来の改善候補 (Future)
- PBR・配当利回りなどのバリューファクター追加。
- OpenAI 呼び出しの並列化・コスト最適化。
- モデル選択やプロンプト最適化の自動化、より詳細な品質チェックのルール追加。

---

（この CHANGELOG は、このリポジトリ内のソースコードから推測して作成された初期リリースの要約です。実際のリリースノート作成時は、変更差分やコミット履歴に基づく追記・修正を推奨します。）