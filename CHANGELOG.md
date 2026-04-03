# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-03

初期リリース。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定 / 環境変数読み込み (kabusys.config)
  - .env ファイル（.env, .env.local）または OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントなどに対応。
    - .env.local は .env の上書き（override=True）として扱い、OS 環境変数は保護（protected）される。
  - Settings クラスを提供し、以下の主要設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須とし未設定時は ValueError）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知関連）
    - duckdb/sqlite のデータパス、監視用 PID/KILL フラグのパス、閾値設定（CPU/Memory/Disk）
    - 実行環境判定（development / paper_trading / live）および LOG_LEVEL のバリデーション
  - 環境設定は明確なエラーメッセージとバリデーションを備える。

- データ基盤・ETL（kabusys.data）
  - ETL 結果を表す ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
  - pipeline モジュール:
    - 差分取得、バックフィル、品質チェックの設計を反映した ETLResult とユーティリティを実装。
    - DuckDB を使ったテーブル存在チェックや最大日付取得などのユーティリティを提供。
    - バックフィルやカレンダー先読みなど現実運用を意識したパラメータを導入。

- 市場カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。
    - J-Quants クライアントから差分取得し、market_calendar テーブルへ冪等更新。
    - バックフィル・健全性チェック（未来日付の異常検出）を備える。
  - 営業日判定ユーティリティを提供:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にデータがある場合は DB 値を優先、未登録日は曜日ベースのフォールバック（週末除外）
    - 最大探索範囲を設け無限ループを防止

- AI ベースのニュース解析（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価して ai_scores テーブルへ書込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事かつ 3000 文字にトリム。
    - JSON mode を想定したレスポンス検証（results 配列・code/score の検証）、スコアは ±1.0 にクリップ。
    - リトライ/バックオフ: 429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフで再試行。致命的でない場合はスキップして処理継続（フェイルセーフ）。
    - テスト容易性のため _call_openai_api を unittest.mock.patch で差し替え可能な設計。
    - DuckDB の executemany の空リスト制約への対応（空のときは実行しないガード）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書込み。
    - マクロニュースはニュース NLP の calc_news_window を利用して期間を算出し、マクロキーワードでフィルタしたタイトルを LLM に渡して評価（gpt-4o-mini、JSON 出力）。
    - LLM 呼び出しはリトライ付きで、失敗時は macro_sentiment=0.0 をフォールバック（例外を上げない）。
    - lookahead bias 回避設計: date 比較は target_date 未満など排他条件を用い、datetime.today() を参照しない。
    - OpenAI クライアントは直接 OpenAI(api_key=...) を生成。

- リサーチ機能（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時は None を返す設計。
    - 計算は prices_daily / raw_financials のみ参照し、実取引 API にはアクセスしない。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）のリターンを返す。horizons のバリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関（ランク化ユーティリティ rank を含む）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計サマリ機能。
    - 実装は外部ライブラリに依存せず標準ライブラリ＋DuckDBで動作。

### 設計上の注意・仕様
- DuckDB を主要なオンディスク DB として利用。executemany の空リストバインドに対する互換性処理を実装。
- OpenAI との対話は JSON mode を前提にし、レスポンスに対する堅牢なパースとバリデーションを実施。API の障害・レート制限に対してはリトライとフェイルセーフ（スコア 0.0 / スキップ）を採用し、パイプライン全体の継続性を優先。
- ルックアヘッドバイアス防止: どの AI / 計算処理も内部で datetime.today() や date.today() を用いず、caller が与える target_date に基づいて処理を行う。
- テストフレンドリーな設計:
  - OpenAI 呼び出し箇所はモック差替え（patch）可能に実装。
  - 環境変数自動ロードはテスト用に無効化可能。

### 既知の制約 / 将来検討事項
- 現バージョンでは PBR・配当利回りなど一部バリューファクターは未実装（calc_value に注記あり）。
- news_nlp における LLM レスポンスの補完処理は実用的だが、より厳密なスキーマ検証やスキーマ駆動のエラー報告を将来的に検討。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）に依存。API 側の変更に注意。

### 破壊的変更
- なし（初期リリース）

---

今後のリリースでは、バグ修正、性能改善、追加ファクターや運用ツール（監視・アラート）などを追記していきます。