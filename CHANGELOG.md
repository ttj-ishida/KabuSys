KEEP A CHANGELOG 準拠の CHANGELOG.md（日本語）を以下に作成しました。リポジトリ内のコードから機能・設計意図を推測して記載しています。

CHANGELOG.md
=============
すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

フォーマット:
- 追加: 新規機能
- 変更: 既存機能の変更
- 修正: バグ修正
- 非推奨: 使用が非推奨になった機能
- 削除: 削除された機能
- セキュリティ: セキュリティに関する変更

<!-- Unreleased セクションを将来の変更用に残します -->
## [Unreleased]
- なし

## [0.1.0] - 2026-03-29
初回公開リリース。

### 追加
- パッケージの基本セットアップ
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - パブリックモジュールエクスポート: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル（.env / .env.local）および OS 環境変数からの設定自動読み込み機能を実装。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - プロジェクトルートの検出: .git または pyproject.toml を基準に __file__ から探索。
  - .env 行パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - .env 読込み時の上書き制御: .env は既存変数を保護、.env.local は上書き。OS 環境変数は protected。
  - Settings クラスを提供（settings オブジェクト経由で使用可能）:
    - J-Quants / kabuステーション / Slack / DB（DuckDB / SQLite） / ログレベル / 実行環境（development/paper_trading/live） 等の取得プロパティ
    - 必須設定未指定時は ValueError を投げるヘルパーを用意

- AI ニュース解析 (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols より銘柄別にニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）へ送信してセンチメント（-1.0〜1.0）を算出。
  - ニュース収集ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を calc_news_window で算出。
  - バッチ処理: 最大 _BATCH_SIZE（20）銘柄ずつ API 送信。1銘柄あたりの記事数上限・文字数上限（トリム）を実装。
  - 再試行（リトライ）ロジック: 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフ。
  - レスポンスの厳密バリデーション: JSON 抽出、results キー、code/score 型チェック、スコアをクリップ（±1.0）。
  - DB 書き込みは冪等化（DELETE → INSERT）し、部分失敗時に既存データを保護。
  - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
  - score_news は書き込み済み銘柄数を返す（0 のフォールバックを含む）。

- AI 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とニュースベースの LLM マクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - ma200_ratio の計算は target_date 未満（排他）のデータのみを利用し、ルックアヘッドバイアスを排除。
  - マクロニュース抽出は news_nlp.calc_news_window に従い raw_news からマクロキーワードでフィルタ。
  - OpenAI 呼び出しは独自の実装でテストフックあり。API 失敗時は macro_sentiment=0.0 を採用するフェイルセーフ。
  - LLM 呼び出しに対するリトライ（RateLimit/API接続/タイムアウト/5xx）とログ出力。
  - market_regime テーブルへの書き込みはトランザクションを用いた冪等操作（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行。

- データプラットフォーム: カレンダー / ETL / パイプライン (src/kabusys/data/*)
  - calendar_management:
    - JPX カレンダー管理（market_calendar）: 営業日判定、前後営業日の検索、期間内営業日リスト、SQ判定等のユーティリティを提供。
    - DB データがない場合の曜日ベースフォールバック（土日を非営業日扱い）。
    - next_trading_day / prev_trading_day は DB 登録値優先、未登録日は曜日ベースにフォールバック。最大探索日数上限を設定して無限ループを防止。
    - calendar_update_job: J-Quants から差分取得し冪等保存（バックフィル・健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスを提供（ETL 実行結果、品質問題、エラー集計を保持）。
    - 差分更新、バックフィル、品質チェック（quality モジュールを利用）等の設計方針を定義。
    - DuckDB を用いる前提で最終日付取得やテーブル存在チェック等のユーティリティを実装。
  - data/etl は ETLResult を公開インターフェースとして再エクスポート。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research:
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）
    - ボラティリティ/流動性: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率
    - バリュー: PER（EPS が 0 または欠損の場合は None）、ROE（raw_financials から最新を取得）
    - DuckDB の SQL ウィンドウ関数を中心に実装（外部 API へはアクセスしない）。
    - 計算結果は (date, code) を含む dict のリストで返す。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応。引数バリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を内部実装（外部ライブラリに依存しない）、有効レコードが 3 未満なら None を返す。
    - ランキング関数 rank（同順位は平均ランクに処理）。
    - 統計サマリー関数 factor_summary（count/mean/std/min/max/median）。
  - research パッケージ __init__ で主要関数（calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize）を再エクスポート。

### 変更
- 初回リリースのため過去リリースからの変更はなし（新規追加）。

### 修正
- 初回リリースのため既知のバグ修正履歴はなし。

### 設計上の注意点（ドキュメント化）
- ルックアヘッドバイアス対策:
  - news_nlp, regime_detector を含む主要処理は datetime.today()/date.today() を直接参照せず、外部から target_date を受け取る設計。
  - prices_daily クエリは target_date 未満（排他）や LEAD/LAG による営業日ベースの計算を行い未来データ参照を防止。
- フェイルセーフ:
  - OpenAI API 失敗時は局所的に安全なデフォルト（例: macro_sentiment=0.0）を使い続行する設計。
  - DB 書き込みはトランザクション保護・部分書き込み回避のため対象コードに絞って DELETE → INSERT を行う。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api）をパッチ可能にしてユニットテストを容易化。
- DuckDB 互換性:
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約）等、実装上の互換性考慮。

### 既知の制限 / TODO
- strategy / execution / monitoring パッケージは __all__ に列挙されるが、本リリースのスナップショットにおける具体的な実装は限定的（本 CHANGELOG はコードベースから推測して作成）。
- 一部の機能（例: PBR・配当利回り等のバリューファクター）は未実装で将来的な拡張余地あり。

---

作成にあたっての補足:
- 上記は提供されたソースコードの内容（関数、ドキュメンテーション文字列、定数、ログ出力など）から推測した機能説明・設計方針を反映しています。
- 実際のリポジトリのコミット履歴や外部ドキュメントが存在する場合は、それに合わせて差分・日付を更新してください。