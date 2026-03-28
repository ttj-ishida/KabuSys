# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このリポジトリの初期リリースに相当する変更点を、コードベースから推定してまとめています。

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期公開
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - パッケージの主要サブパッケージ（data, research, ai, etc.）を __all__ でエクスポート。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない設計。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - 環境変数の自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 既存 OS 環境変数を保護するための protected キーセットを考慮した上書き処理を実装。
  - 必須環境変数チェック関数 `_require` を実装し、未設定時は ValueError を送出。
  - Settings クラスを提供し、J-Quants/Slack/kabuステーション/DBパス/環境種別（development/paper_trading/live）/ログレベル等のプロパティを取得可能にした。
    - env / log_level のバリデーションを実装（不正値は ValueError）。
    - DuckDB/SQLite のデフォルトパス（data/kabusys.duckdb, data/monitoring.db）を設定。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols をソースに、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメント評価を行い、ai_scores テーブルへ書き込む機能を実装。
    - 日次のニュースウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）と、それに基づく記事抽出ロジックを提供（calc_news_window）。
    - API 呼び出しはバッチ（最大 20 銘柄/回）で実行し、1銘柄最大記事数・文字数でトリムする保護を導入。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。
    - OpenAI レスポンスのバリデーション（JSON モードの余計な前後テキスト対策含む）、スコアクリップ（±1.0）、不正レスポンス・失敗時のフェイルセーフ（スキップまたは 0 相当）を実装。
    - 書き込みは部分失敗に強い処理（対象コードのみ DELETE → INSERT）とし、DuckDB の executemany 空リスト制約に対する配慮を行う。
    - テスト容易性のため、内部の API 呼び出し関数を patch 可能に設計。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio 計算、マクロニュース抽出（キーワードフィルタ）、OpenAI（gpt-4o-mini）呼び出し、合成スコア化、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 とするフェイルセーフ実装。内部での retry/backoff を実装。
    - OpenAI クライアント生成は api_key 引数または環境変数 OPENAI_API_KEY を参照。
    - look-ahead バイアス回避のため、target_date 未満のデータのみ使用する設計。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB クエリで計算する関数を追加。
    - データ不足時は None を返す扱い、結果は (date, code) をキーとする dict のリストとして返却。
    - DuckDB SQL を多用し、外部 API への依存を排除。

  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク化（同順位の平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 入力バリデーション（horizons の型/範囲チェック、最小有効レコード数チェック）を導入。
    - pandas 等に依存せず、標準ライブラリと DuckDB のみで実装。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定ロジックを実装（market_calendar テーブル優先、未登録日は曜日フォールバック）。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等更新する処理を追加（バックフィル、健全性チェックを含む）。
    - DB 未取得時でも一貫したフォールバック挙動を保持する設計。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを追加し、ETL のフェッチ・保存結果、品質問題、エラー一覧を集約して返却可能に。
    - テーブル存在チェック／最大日付取得などのユーティリティ関数を実装。
    - data.etl モジュールから ETLResult を再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の取り扱いで OS 環境を保護する protected キーセットを導入（.env の上書きを制御）。

### Notes / Design decisions
- ルックアヘッドバイアス回避: AI/NLP/ファクター計算のすべての関数は内部で datetime.today()/date.today() を参照せず、呼び出し元から target_date を受け取る設計としている点を強調。
- OpenAI 呼び出し: JSON Mode を利用しつつもパース時の冗長テキスト対策を実装（堅牢なパース設計）。
- DB 書き込み: 部分失敗時に既存データを不必要に削除しないため、対象コードを限定して DELETE → INSERT を行う安全設計。
- テスト性: OpenAI 呼び出し箇所を内部関数として抽象化し、テストで差し替え可能にしている。

### Known limitations / TODO
- 一部のファクター・指標（例: PBR、配当利回り）は現バージョンで未実装（calc_value の注記参照）。
- strategy / execution / monitoring サブパッケージは __all__ に含まれているが、今回提示されたコードベース内では内容を示していないため、将来の実装/ドキュメント追加が見込まれる。

---

この CHANGELOG は提供されたソースコードの実装内容から推定して作成しています。実際のコミット履歴や設計ドキュメントがあれば、そちらに基づいてより正確に更新してください。