# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

注: この CHANGELOG は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]
- 開発中の変更点や次回リリースでの予定事項をここに記載してください。

## [0.1.0] - 2026-04-04
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期モジュール構成を追加。公開 API として data, strategy, execution, monitoring を __all__ に定義（src/kabusys/__init__.py）。
  - バージョン情報を __version__ = "0.1.0" として設定。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local を自動ロードする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - プロジェクトルート自動検出 (.git / pyproject.toml に基づく) によりカレントワーキングディレクトリに依存しない自動読み込みを実現。
  - .env パーサ実装: export 形式、クォート内のエスケープ、インラインコメント処理等に対応。
  - 必須環境変数チェック用の _require と Settings クラスを提供。J-Quants / kabu API / LINE / DB /監視 /システム設定などのプロパティを用意。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL など）と便利な bool プロパティ（is_live, is_paper, is_dev）を実装。

- ニュース NLP / AI 統合 (src/kabusys/ai/*.py)
  - news_nlp モジュールを追加し、raw_news + news_symbols から記事を集約して OpenAI (gpt-4o-mini) にバッチ送信、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST の記事）
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄あたり記事数・文字数トリム対応
    - JSON Mode レスポンスのバリデーションと堅牢なパース（余計な前後テキストの補正）
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで処理
    - DuckDB への冪等的な書き込み（DELETE → INSERT、部分失敗時の既存データ保持）
    - テスト用に _call_openai_api を差し替え可能
  - regime_detector モジュールを追加し、ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジームを判定・保存する機能を実装。
    - ma200_ratio の計算（target_date 未満データを使用しルックアヘッドを防止）
    - raw_news からマクロキーワードでニュース抽出
    - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得、API失敗時はフォールバック 0.0
    - スコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - API 呼び出しの再試行と 5xx 判定対応、テストで差し替え可能な内部呼び出し

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算。データ不足時の扱い明示。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials から最新の eps/roe を取得して PER/ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB を用いた SQL+ウィンドウ関数ベースの実装。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを取得（LEAD を使用）。
    - calc_ic: Spearman ランク相関（IC）を計算するユーティリティ（None/不足レコードの扱いを定義）。
    - rank, factor_summary: ランク付け、統計サマリー（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - research パッケージの公開 API を整備（zscore_normalize を data.stats から再公開等）。

- データプラットフォーム (src/kabusys/data/*)
  - calendar_management: JPX 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）と夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - market_calendar が未取得の際の曜日ベースのフォールバック、DB 値優先の一貫した挙動。
    - API 取得 → 保存の流れ（J-Quants クライアント経由）と健全性チェック / バックフィル。
  - pipeline / etl: ETLResult データクラスと ETL パイプラインの骨組みを追加。
    - 差分更新、バックフィル、品質チェックのための構造を提供。
    - ETLResult に to_dict / エラー・品質判定プロパティを提供。
  - etl モジュールの公開インターフェース（ETLResult の再エクスポート）。

### 変更 (Changed)
- 全体設計面の記載（ドキュメンテーション的な説明をソース内ドキュメントとして整備）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を内部ロジックで参照しないよう注意書きや実装方針を明確化。
  - DuckDB をデータ層の中心として想定し、SQL と Python を併用した実装方針を採用。
  - OpenAI 呼び出し周りはモジュール間でプライベート関数を共有せず、テストで差し替えやすい設計に。

### 修正 (Fixed)
- API 呼び出しに関する堅牢性向上
  - OpenAI 応答の JSON パース失敗や非標準出力（前後テキスト混入）への対処を実装。
  - リトライ／バックオフ戦略を導入し、一時障害時はフェイルセーフで処理を継続（スコアは 0.0 にフォールバックなど）。
- DuckDB への書き込みを冪等化（DELETE → INSERT のパターン、トランザクション制御、ROLLBACK での安全確保）。
- .env 読み込みでファイル読み込み失敗時に warnings.warn を発行するようにして静的失敗を回避。

### セキュリティ (Security)
- 環境変数による機密情報管理を前提（OpenAI API キー / J-Quants / Kabu のトークン/パスワード 等）。
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI での誤読み込み防止）。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI API を使用する機能（news_nlp / regime_detector）は API キーが必須。api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合は ValueError を送出。
- 一部の関数はテストしやすいように内部 API 呼び出しを差し替える設計だが、実環境では適切なキーと DuckDB スキーマが必要。
- strategy / execution / monitoring の具体的実装ファイルはこのスナップショットに含まれていない（パッケージの公開名に含めてあるため将来的に実装予定）。

---

参考: この CHANGELOG はソースコードのドキュメント文字列、関数名、実装コメント、ログメッセージから推測して作成しています。必要であればリリースノートをさらに細分化（ファイル単位の変更履歴や開発者向けの移行手順追記）できます。