# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」のフォーマットに準拠します。

変更履歴のポリシー:
- バージョンは package の __version__ に合わせています。
- 日付は本リリース作成日です（自動生成時は適宜更新してください）。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初回公開リリース。日本株自動売買システムの基盤となる以下の主要機能を実装・公開。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - __all__ に data/strategy/execution/monitoring を公開（将来的なモジュール構成を想定）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env, .env.local）および OS 環境変数からの読み込みを自動化。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索。
  - .env パーサ: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 必須設定取得ヘルパー: Settings クラスを提供（プロパティ経由で以下を取得）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - ヘルパー: is_live / is_paper / is_dev

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST を採用（UTC 変換あり）。
    - バッチ処理: 最大 20 銘柄/リクエスト、1銘柄あたり最大 10 記事・3000 文字に制限。
    - レスポンスは JSON mode を期待し、堅牢なパースとバリデーションを実装。
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして他銘柄は継続。戻り値は書き込んだ銘柄数。
    - テスト用フック: _call_openai_api を patch してモック可能。
    - DuckDB の executemany に関する注意点（空リスト不可）を考慮して実装。

  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と
      マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull/neutral/bear）。
    - ma200_ratio は target_date 未満のデータのみ使用（ルックアヘッド回避）。
    - マクロ記事抽出はマクロキーワード一覧でフィルタし、最大 20 記事を LLM に渡す。
    - OpenAI 呼び出しは独立実装。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。

- リサーチ（ファクター計算）モジュール (kabusys.research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を参照して PER/ROE を算出（PBR/配当は未実装）。
    - 全関数は prices_daily / raw_financials のみ参照し、外部 API にアクセスしない。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を算出。利用可能レコードが 3 未満で None を返す。
    - rank: 同順位は平均ランクを返す実装（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出。
  - research パッケージ __init__ で主要関数を再エクスポート。

- データ基盤（Data）モジュール (kabusys.data)
  - calendar_management.py
    - JPX カレンダー管理ロジック（market_calendar テーブルの使用を想定）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にデータがない場合は曜日ベース（平日のみ営業日）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得 → 保存（jq.fetch_market_calendar / jq.save_market_calendar を利用）・バックフィル・健全性チェックを実装。
  - pipeline.py / ETLResult
    - 差分取得と保存、品質チェックのための ETLResult データクラスを実装。
    - _get_max_date 等のユーティリティを提供。
  - etl.py
    - pipeline.ETLResult を公開インターフェースとして再エクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意 (Notes)
- ルックアヘッドバイアス回避:
  - AI モジュール・研究モジュールは内部で datetime.today()/date.today() を参照せず、外部から与えられた target_date の過去データのみを参照する設計。
- OpenAI API の取り扱い:
  - API キーは各関数の api_key 引数で注入可能。None の場合は環境変数 OPENAI_API_KEY を参照。
  - API 失敗時のフェイルセーフ（0.0 やスキップ）により、ETL やスコアリング全体が一度の外部障害で停止しないように設計。
- テスト容易性:
  - news_nlp と regime_detector の _call_openai_api はそれぞれ独立実装かつパッチ可能にしてあり、ユニットテストでモックしやすい。
- DB（DuckDB）互換性:
  - DuckDB の executemany に空リストを渡すと失敗する既知の制約を考慮して NULL チェックを行っている。
- 環境変数と自動読み込み:
  - パッケージはインポート時にプロジェクトルートを検出して .env ファイルを自動読み込みする（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 自動読み込みは OS 環境変数を保護（.env ファイルで既存の env を上書きしない / .env.local は上書きするが OS env は保護）する挙動。

### 既知の制約・今後の作業
- news_nlp の出力で期待される JSON スキーマ（results の各要素に code/score）が守られない場合はそのチャンクをスキップする。将来的により詳細なエラーメトリクス収集を追加予定。
- calc_value では現時点で PBR・配当利回りは未実装。
- monitoring や strategy / execution パッケージの詳細実装は今後拡張予定（__all__ で公開予定）。
- J-Quants クライアント（kabusys.data.jquants_client）と quality モジュールは外部依存として想定され、環境に合わせた実装が必要。

### セキュリティ (Security)
- API キー等の機密情報は環境変数経由で取得する設計。誤ってコード内に埋め込まないこと。
- .env をリポジトリに含めないよう注意（.env.example を参照して設定することを推奨）。

---

（必要に応じて各機能の詳細な使い方・マイグレーション手順を別ドキュメントに記載してください。）