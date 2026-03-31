# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムの基礎機能を実装しました。主な追加点・設計方針・安全対策は以下の通りです。

### 追加 (Added)
- パッケージ骨格
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンを "0.1.0" として公開。
  - サブパッケージのエクスポートに data, strategy, execution, monitoring 等を想定。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロード機能：プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を読み込む（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサ実装：export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いをサポート。
  - 上書き制御：.env.local は override=True で読み込むが OS 環境変数は protected として保護。
  - 各種設定プロパティ（J-Quants、kabuAPI、Slack、DBパス、監視閾値、環境・ログレベル判定等）を用意し、妥当性検証を行う（例：KABUSYS_ENV, LOG_LEVEL の検証）。未設定必須値は _require() により ValueError を送出。

- AI：ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を用い、銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメント（ai_score）を算出する score_news を実装。
  - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数トリム（デフォルト最大10記事・3000文字）によりトークン肥大を抑制。
  - 再試行（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。非再試行エラーはスキップして継続（フェイルセーフ）。
  - レスポンス検証ロジック（JSON復元・resultsキー検査・コード照合・スコア数値化・±1.0クリップ）を実装。
  - DuckDB への書き込みは部分置換（該当コードのみ DELETE → INSERT）で冪等性・部分失敗耐性を確保。DuckDB executemany の空配列制約を回避するチェックを実装。
  - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST を UTC に変換）を calc_news_window に実装。
  - テスト容易性：OpenAI 呼出し部分は内部関数をモック可能（unittest.mock.patch 対応）。

- AI：市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - MA200 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。データ不足時は中立値（1.0）を採用し WARNING ログを出力。
  - マクロニュース抽出はキーワードベースでフィルタ（設定上限20件）し、LLM により -1.0〜1.0 のマクロセンチメントを算出。API失敗時は 0.0 でフォールバック。
  - 合成スコアはクリップ処理後に閾値でラベル付け。DuckDB への書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保し、例外時は ROLLBACK を試行して上位に伝播。

- データ基盤（src/kabusys/data/**）
  - ETL インターフェース／結果（ETLResult dataclass, pipeline.ETLResult を etl.py で再エクスポート）。
  - pipeline モジュール：差分取得、バックフィル、品質チェック（quality モジュール連携想定）を行う設計。結果集約用の ETLResult を提供。
  - 市場カレンダー管理（calendar_management.py）：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を行う。J-Quants クライアント経由での夜間更新ジョブ calendar_update_job を実装し、バックフィル＆健全性チェックを行う。

- 研究用モジュール（src/kabusys/research/**）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials のみを参照して各種ファクター（モメンタム、MA200乖離、ATR、出来高・売買代金指標、PER/ROE）を算出。
  - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（スピアマンランク相関によるIC）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - データ処理は DuckDB SQL を活用し、外部ライブラリ（pandas 等）に依存しない実装。

### 変更 (Changed)
- 設計方針の明示
  - AI / 研究 / ETL の重要な関数は内部で datetime.today() や date.today() を直接参照せず、明示的な target_date 引数で動作するようにしてルックアヘッドバイアスを排除。
  - OpenAI 呼び出しのエラーハンドリングは明示的に分類（RateLimit/Connection/Timeout はリトライ、APIError は status_code に応じて扱い分け）して安全性を高めた。

### 修正 (Fixed)
- DB トランザクション安全性
  - 複数箇所で DB へ書き込む処理にトランザクションと ROLLBACK の試行を追加。ROLLBACK が失敗した場合はログに警告を出力して上位に例外を伝播。
- DuckDB 互換性
  - executemany に空リストを渡すとエラーになる問題に対処するため、空リスト時は実行をスキップするガードを追加（ai/news_nlp, pipeline 等）。
- .env パースの堅牢化
  - クォート／エスケープ／コメント処理を改善し、export プレフィックスへの対応を追加。

### セキュリティ (Security)
- API キー取り扱い
  - OpenAI API キーは明示的に引数で注入可能（テスト容易化）で、未設定時は ValueError を送出。環境変数のみの探索に依存しない仕様により誤設定時の早期発覚を促進。

### ドキュメント（設計ノート）
- 各モジュールに詳細な docstring を追加し、処理フロー・設計方針・フォールバック挙動を明記。これにより保守性・テスト容易性を向上。

---

注記:
- 本 CHANGELOG は提供されたソースコードから実装意図・機能を推測して作成しています。実際のリリースノート作成時は差分（git log や実際のコミットメッセージ）に基づいて調整してください。