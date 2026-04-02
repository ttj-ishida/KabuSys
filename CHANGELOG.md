CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠します。

Unreleased
----------
- 既知の問題 / 今後対応予定
  - data.pipeline._get_max_date 関数で実装途中のタイポ（return date.fro）が確認されます。ETL パイプライン内で最大日付取得が必要な箇所に影響する可能性があるため修正予定です。
  - data パッケージの __init__.py が未実装の状態で、公開 API の整理（再エクスポート）の整備が必要です。
  - ドキュメント整備（API 使用例、マイグレーション手順など）を強化予定。

[0.1.0] - 2026-04-02
--------------------
Added
- パッケージの初期公開（kabusys v0.1.0）
  - パッケージルート: src/kabusys/__init__.py にて __version__ = "0.1.0"、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ として公開。

- 環境設定管理（src/kabusys/config.py）
  - .env と .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val 形式やシングル/ダブルクォート内のバックスラッシュエスケープ、行末コメント処理等に対応した .env パーサ実装。
  - override / protected オプションによる環境変数上書き制御。
  - settings オブジェクトを公開し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）のバリデーション付きプロパティを提供。
  - 必須環境変数未設定時に ValueError を投げる _require ヘルパを追加。

- AI（自然言語処理）モジュール（src/kabusys/ai/）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへセンチメントを書き込む処理を実装。
    - タイムウィンドウ計算（calc_news_window）: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱うロジックを提供。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数、チャンク毎のリトライ（429/ネットワーク/タイムアウト/5xx）を考慮した堅牢な API 呼び出し。
    - OpenAI の JSON Mode 応答のバリデーション（results 配列 / code, score の存在・型チェック）、数値の有限性チェック、スコアを ±1 にクリップして保存。
    - 部分失敗に配慮し、ai_scores の置換（DELETE → INSERT）をコード単位で実行して既存データを保護。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの ma200_ratio 計算、raw_news からのマクロキーワード抽出、OpenAI（gpt-4o-mini）呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 低信頼時のフォールバック（macro_sentiment=0.0）、API リトライ（指数バックオフ）や 5xx 処理、JSON パース失敗時の安全処理を実装。
    - ルックアヘッドバイアス防止のため target_date 未満のデータのみ参照する設計。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ユーティリティ（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を実装。
    - DB にデータがない場合は曜日（平日）ベースでフォールバックする堅牢な設計。
    - calendar_update_job による J-Quants からの差分取得 / 冪等保存（バックフィル・健全性チェック含む）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult dataclass を公開（etl.ETLResult を再エクスポート）し、ETL の集計結果・品質問題・エラー概要を表現。
    - 差分更新の設計（バックフィル日数、品質チェックを継続的に収集する方針）を実装。
    - 注意: _get_max_date 実装末尾にタイポがあり未完（Unreleased の既知問題参照）。
  - jquants_client インターフェース呼び出し部分を想定した実装（fetch/save 呼び出しを想定）。

- リサーチ（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、20 日平均売買代金・出来高比率等のファクター計算を実装。
    - Data は prices_daily / raw_financials のみを参照し、データ不足時は None を返す設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）とランク変換（rank）を実装。
    - pandas 等に依存せず純粋 Python + DuckDB SQL 実装を採用。

Changed
- N/A（初期リリースのため履歴なし）

Fixed
- N/A（初期リリースのため履歴なし）

Security
- 外部に平文トークンを露出しない方針で環境変数管理を実装。自動ロードは環境変数で無効化可能。

Notes / 実装上の設計方針
- ルックアヘッドバイアス防止: 各モジュール（AI スコア/レジーム判定/ファクター計算）は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
- OpenAI 呼び出しは JSON Mode を使い厳密な JSON を期待するが、応答が不正な場合にロバストに処理する保護（JSON の抽出やパース失敗時のフォールバック）を実装。
- DuckDB を主要なローカル DB として利用。executemany の空リストバインド制約（DuckDB 0.10）に配慮した実装。
- テスト容易性: OpenAI 呼び出し関数はモジュール内でラップしており、unittest.mock.patch により差し替え可能。

Authors
- このリリースはリポジトリ内のソースコード注釈と実装から推測して作成しました。実際のリリースノートはリポジトリのメンテナが確定してください。