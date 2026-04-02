# Changelog

全ての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-02

初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を実装しました。
主にデータ取得/ETL、マーケットカレンダー管理、ファクター計算・研究用ユーティリティ、
および OpenAI を用いたニュース NLP / 市場レジーム判定の機能を含みます。

### Added
- 基本パッケージ構成
  - src/kabusys/__init__.py にバージョン情報と公開モジュール一覧を追加（__version__ = "0.1.0"）。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定をロードする自動ローダ実装（プロジェクトルート検出：.git / pyproject.toml）。
  - export KEY=val 形式・クォートやエスケープ、インラインコメントの取り扱いに対応した .env パーサ実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須項目取得用の _require と Settings クラス実装（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境検証など）。
  - KABUSYS_ENV と LOG_LEVEL の検証ロジック実装（許容値チェック）。
- AI（ニュースNLP・レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数・文字数制限、JSON Mode を利用したレスポンス検証を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、レスポンスの堅牢なバリデーション（JSON 部分抽出・型チェック・既知コードのみ採用）を実装。
    - DuckDB の executemany 空リスト制約に対する対処（空チェック）を実装。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計。タイムウィンドウは JST を基準に UTC naive で計算（前日 15:00 JST ～ 当日 08:30 JST）。
    - テスト容易性のため OpenAI 呼び出しの差し替えポイント（kabusys.ai.news_nlp._call_openai_api）を明示。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - prices_daily からのデータ取得は target_date 未満のみを参照してルックアヘッドを防止。
    - OpenAI 呼び出し失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ実装。
    - retry / backoff やレスポンスパースの堅牢化、テスト用差し替えポイントを用意。
- データプラットフォーム（src/kabusys/data）
  - calendar_management.py
    - market_calendar を用いた JPX カレンダー管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB データがない場合は曜日ベースでフォールバック。
    - calendar_update_job により J-Quants から差分取得して冪等に保存する夜間バッチ処理を実装（バックフィル・健全性チェック含む）。
  - pipeline.py
    - ETLResult dataclass を含む ETL パイプライン用ユーティリティを実装。差分取得・保存・品質チェックのための土台を用意。
    - ETLResult に to_dict / エラー・品質チェック集約のフィールドを実装。
  - etl.py
    - pipeline.ETLResult の再エクスポートを追加。
  - jquants_client などのクライアントはモジュール参照ポイントとして利用（calendar_management から import）。
- Research（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、Value（PER/ROE）などのファクター計算を実装。DuckDB の SQL ウィンドウ関数を活用。
    - データ不足時の None 扱い、ルックアヘッドバイアス回避設計。
  - feature_exploration.py
    - 将来リターン計算（複数ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、ランク変換ユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で完結する実装。
  - __init__.py に研究用 API の再エクスポートを追加（zscore_normalize など）。
- その他
  - テスト・モック用に OpenAI 呼び出し部分の差し替えポイントを明示（news_nlp._call_openai_api / regime_detector._call_openai_api）。
  - DuckDB 特有の挙動（executemany の空リスト不可）への対応を実装。

### Changed
- 設計上の方針・安全装置を明示
  - 全ての AI/スコアリング処理でルックアヘッドバイアスを避けるため、関数は内部で現在時刻を参照せず、target_date ベースでウィンドウを計算する実装に統一。
  - OpenAI のレスポンスパースや API エラー処理を一貫して実装（5xx はリトライ、その他はフォールバックまたはスキップ）。
  - DB 書き込みは基本的に冪等（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）で行う方針を採用。

### Fixed
- データ不備や API 障害時のフェイルセーフ実装を追加
  - ニュースや ETF データ不足時は中立値（例: ma200_ratio=1.0、macro_sentiment=0.0）で継続するようにし、例外で処理が停止しないよう改善。
  - DuckDB での executemany 空リスト問題に対して事前チェックを行うことで部分書き込み時に他データを消さないよう対処。
  - market_calendar の NULL 値に対して警告ログを残し、曜日ベースのフォールバックを使うようにした。

### Security
- 環境変数の読み込み時に OS 環境変数を保護する "protected" 機構を導入（.env 読み込みで既存 OS 環境変数を上書きしないデフォルト動作）。
- API キー未設定時は明示的な ValueError を投げて失敗原因が分かるようにした（OpenAI、Slack、J-Quants 関連の必須設定）。

### Documentation / Developer experience
- モジュール docstring に処理フロー・設計方針・使用上の注意（ルックアヘッド回避、DuckDB 互換性、テスト差し替えポイントなど）を詳述。
- ロギングを各処理に埋め込み、情報・警告・例外状況を記録するようにした。

### Known limitations / Notes
- OpenAI 呼び出しは gpt-4o-mini を前提とした JSON Mode を使用する実装になっている（API プロバイダ側の変更により動作しない場合は対応が必要）。
- J-Quants クライアント実装（jquants_client）は外部モジュール依存として想定され、実際の API 呼び出し処理はモジュール側で提供される前提。
- 現時点では PBR や配当利回りなど一部バリューファクターは未実装（calc_value に注釈あり）。

---

これ以降のリリースでは、テストカバレッジの強化、エラー監視・リトライの可視化、モデル切替の抽象化、ファクター追加や発注（execution）モジュールの実装などを予定しています。必要であれば、この CHANGELOG を基にリリースノートの詳細化（各コミット/PR からの差分）も作成します。