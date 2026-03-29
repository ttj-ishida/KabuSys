# CHANGELOG

すべての重要な変更点はこのファイルに記載します。  
このプロジェクトでは「Keep a Changelog」形式に従い、セマンティック バージョニングを採用します。

なお、この CHANGELOG はリポジトリ内のソースコードから機能・設計意図を推測して作成しています。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-29

Added
- パッケージ初期リリース。主要コンポーネントを追加。
  - kabusys パッケージ初期化
    - パッケージバージョン: `__version__ = "0.1.0"`
    - パブリック API のエクスポート: `["data", "strategy", "execution", "monitoring"]`
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
  - .env パーサの強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートされた値をバックスラッシュエスケープを考慮して正しくパース。
    - クォートなし値に対するインラインコメントルールを導入（`#` の直前がスペース/タブの場合にコメントとみなす）。
  - .env 読み込みの上書きルール:
    - override=False: 未設定のキーのみセット
    - override=True: OS 環境変数（読み込み時キャプチャしたキー集合）に入っているキーは保護
  - 必須設定の取得ヘルパー `_require` を提供（未設定時は ValueError を送出）。
  - Settings クラス（環境変数からの設定取得）を追加:
    - J-Quants, kabu API, Slack トークン/チャンネル、データベースパス（DuckDB / SQLite）等のプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値以外は ValueError）。
    - is_live / is_paper / is_dev ヘルパーを提供。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
    - ウィンドウ定義（JST 基準）:
      - 対象期間: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime で扱う）
    - バッチ処理設計:
      - 1API呼び出しあたり最大銘柄数: 20（_BATCH_SIZE）
      - 各銘柄: 最大 10 件の最新記事、最大 3000 文字にトリム
      - JSON Mode を用いた厳密な JSON 出力を期待（出力検証・復元ロジックあり）
    - エラー処理 / 再試行:
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行（デフォルト 3 回）
      - 再試行失敗時はそのチャンクをスキップし、例外を上位に伝播させず継続（フェイルセーフ）
    - レスポンス検証:
      - results リストの存在確認、各要素の code/score 検証、スコアを ±1.0 にクリップ
    - DB 書き込みは冪等化:
      - 成功したコードのみを DELETE → INSERT（トランザクションで囲む）
      - DuckDB の executemany の制約（空リスト不可）に配慮
    - テスト容易性:
      - OpenAI 呼び出しを行う内部関数を patch 可能にしてテスト用置換を想定
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出はキーワードベースで raw_news のタイトルから取得（最大 20 記事）。
    - OpenAI（gpt-4o-mini）に JSON レスポンスを要求し、API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時は ROLLBACK を行い例外を伝播。
- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
      - データ不足時は None を返す（安全処理）。
    - Volatility / Liquidity: 20 日 ATR（単純平均）、relative ATR（atr_pct）、20 日平均売買代金、出来高比率
      - true_range 計算は high/low/prev_close のいずれかが NULL の場合は NULL として扱い、カウントで不足を検出。
    - Value: raw_financials から直近の財務情報を取得し PER / ROE を算出（EPS が 0/欠損時は None）。
    - 全て DuckDB（prices_daily / raw_financials）ベースで実行し、外部 API にはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（デフォルト horizons=[1,5,21]）
      - 単一クエリで複数ホライズンを取得、スキャン範囲は max_horizon の 2 倍のカレンダー日で限定。
    - IC（Information Coefficient）計算 calc_ic（Spearman の rank コリレーション）
      - None 値や非有限値を除外、十分なサンプルがない場合は None を返す。
    - rank ユーティリティ: 同順位は平均ランクに変換（丸めによる ties の扱いに配慮）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を純粋な標準ライブラリのみで計算
  - 研究用に zscore_normalize を data.stats から再利用可能にエクスポート
- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルがない場合は曜日ベースのフォールバック（週末は非営業日）を一貫して使用。
    - next/prev/get_trading_days は DB 登録値を優先しつつ未登録日は曜日フォールバックで補完。探索上限を設けて無限ループを防止。
    - 夜間バッチ calendar_update_job を実装:
      - J-Quants クライアントから差分を取得して market_calendar を冪等保存
      - バックフィル（直近 _BACKFILL_DAYS を再取得）と健全性チェック（未来の日付が極端に大きい場合はスキップ）
      - 取得失敗や保存失敗時は 0 を返す（例外は内部で捕捉しログ出力）
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装し ETL の集計結果（取得数、保存数、品質チェック結果、エラー要約）を返却可能に。
    - 差分取得（最終取得日からの自動算出）、backfill による後出し修正吸収、品質チェック（quality モジュール）の統合方針を定義。
    - 内部ユーティリティで DuckDB テーブル存在チェック・最大日付取得等を実装。
  - jquants_client の保存系関数呼び出しを利用する想定（jq.fetch_market_calendar / jq.save_market_calendar 等）。
- エラーハンドリングとロギング
  - 各所で詳細なログ出力（logger）を実装。API 失敗時のフォールバック動作や ROLLBACK の失敗時の警告ログを追加。

Changed
- 初回リリースのため、既存ライブラリ・設計をコードベースに反映（詳細は各ファイルの docstring / 実装を参照）。

Fixed
- （初回リリースのため適用なし。実装における堅牢性向上を意識した設計を多数導入）

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを実装（.env による上書きから保護）。
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY 経由で解決。未設定時は ValueError を送出して誤使用を防止。

Notes / Implementation details
- 時刻処理はルックアヘッドバイアス防止のため datetime.today() / date.today() の直接参照を避ける設計（関数呼び出し側が target_date を渡す方式）。
- OpenAI 呼び出しは「JSON Mode」を期待して厳格にパースするが、実運用を想定して前後余計テキストの復元ロジックも実装。
- DuckDB のバージョン差異（executemany の空リスト不可、リスト型バインドの挙動等）に配慮した実装。
- テスト容易性のため OpenAI 呼び出しの低レベル関数を patch できる設計。

---

今後のリリースでは以下を予定（例）
- strategy / execution モジュールの実装強化（バックテスト・実注文フロー）
- 監視・アラート（monitoring）の実装拡充（Slack 通知等）
- 品質チェック（quality）ルール拡張とダッシュボード連携

(以上)