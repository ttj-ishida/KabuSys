# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

注: この CHANGELOG はソースコードから推測して作成しています。

## [Unreleased]

（現時点の開発中の変更はここに記載します）

## [0.1.0] - 2026-03-31

初回公開リリース。以下の主要機能とモジュールを追加しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージ名 "KabuSys" とバージョン `__version__ = "0.1.0"` を定義。
    - 公開サブパッケージとして "data", "strategy", "execution", "monitoring" を宣言。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装（プロジェクトルート検出は .git / pyproject.toml を基準）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env/.env.local の読み込みロジック（上書き・保護キーの扱い、エラーハンドリング）。
    - .env 行パーサーの実装（export プレフィックス、クォート・エスケープ、インラインコメント処理に対応）。
    - Settings クラスを導入し、各種必須設定（J-Quants, kabu API, Slack, DB パス、監視閾値、環境種別・ログレベル検証など）をプロパティとして提供。
    - 環境値の妥当性検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を生成する score_news 関数を実装。
    - タイムウィンドウ計算（JST基準で前日15:00〜当日08:30相当）を行う calc_news_window を実装。
    - リクエストを最大 20 銘柄単位でバッチ化（_BATCH_SIZE）、1銘柄あたりのトークン肥大対策（記事数と文字数上限）を実装。
    - API 呼び出しの堅牢性: 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライ、レスポンスのバリデーションと安全フォールバック（失敗時はスキップし続行）。
    - レスポンス検証ロジック（JSON 抽出、results 構造検査、未知コード除外、スコア数値化・クリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時の既存スコア保護、DuckDB executemany の空リスト制約への対応）。
  - src/kabusys/ai/regime_detector.py
    - ETF（1321）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（独立実装）、リトライ・フェイルセーフの実装。
    - DuckDB からの価格取得、MA200 比率計算、レジームスコア合成、market_regime テーブルへの冪等書き込みを実装。
    - 設計方針としてルックアヘッドバイアス防止（date.today()/datetime.today() を参照しない）を明記。

- データプラットフォーム関連
  - src/kabusys/data/pipeline.py
    - ETL パイプラインのインターフェースと処理方針を実装。
    - ETLResult データクラスを導入（フェッチ数／保存数／品質問題／エラー一覧等、has_errors / has_quality_errors / to_dict を提供）。
    - 差分取得・バックフィル・品質チェック方針や DuckDB 依存の注意点を反映。
  - src/kabusys/data/etl.py
    - ETLResult を再エクスポートするインターフェースを追加。
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー（market_calendar）を扱うユーティリティ群を追加。
    - 営業日判定関数: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装（DB 登録値優先、未登録日は曜日フォールバック）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新する夜間バッチジョブを実装（バックフィル、健全性チェック、記録カウントの返却）。
    - market_calendar の未取得時の安全なフォールバックと最大探索日数制限を実装。

- リサーチ（ファクター算出）モジュール
  - src/kabusys/research/factor_research.py
    - ファクター群の計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（MA200 欠損時は None）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（データ不足時は None）
      - calc_value: per（EPS が 0/欠損で None）および roe（raw_financials から最新財務データを取得）
    - DuckDB の SQL ウィンドウ関数を用いた計算実装・データ不足ハンドリング。
  - src/kabusys/research/feature_exploration.py
    - 研究用途のユーティリティを実装:
      - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン取得（存在しない場合は None）
      - calc_ic: スピアマンのランク相関（Information Coefficient）計算（有効レコードが 3 件未満で None）
      - rank: 同順位は平均ランクで処理するランク換算ユーティリティ
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数
    - pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装する方針を採用。
  - src/kabusys/research/__init__.py
    - 主要関数の再エクスポートを追加（zscore_normalize を含む）。

- その他
  - OpenAI と DuckDB を用いた処理フローを多数実装。API キー注入（引数または環境変数 OPENAI_API_KEY）に対応。
  - 多くのモジュールで「ルックアヘッドバイアス防止」の設計方針を明示（date.today()/datetime.today() の不使用）。
  - ロギング出力と詳細な警告メッセージを各所に追加し、障害時の解析を容易にする設計。

### Changed
- 該当なし（初版リリースのためすべて追加）。

### Fixed
- 該当なし（初版リリースのため）。

### Removed
- 該当なし。

### Security
- 該当なし。

---

補足メモ（実装上の注意点／設計意図）
- OpenAI 呼び出しはテスト容易性のため内部で差し替え可能（ユニットテスト用に _call_openai_api を patch することを想定）。
- API 失敗時は可能な限りフェイルセーフ（スコア 0.0 またはスキップ）して全体処理を止めない設計。
- DuckDB に対して executemany に空リストを渡せないバージョン互換性のため、空リストチェックを入れている箇所あり。
- .env パースは多くのシェル記法（export、クォート、エスケープ、コメント）に対応することを意図している。

もし特定ファイルや関数についてより詳細な変更点（例: 実装上の制約や戻り値の詳細、エラーハンドリングの挙動）を CHANGELOG に加えたい場合は、対象箇所を指定していただければ追記します。