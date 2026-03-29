CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

[Unreleased]
-------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリースを公開（パッケージバージョン: 0.1.0）。
- 基本パッケージ構成を追加:
  - kabusys パッケージの公開モジュール群（data, research, ai, 等）。
- 環境設定 / ロード機能:
  - 環境変数読み込みユーティリティを実装（kabusys.config）。
  - プロジェクトルート自動検出（.git / pyproject.toml を探索）。
  - .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサを実装（export プレフィックス、クォート、エスケープ、インラインコメントに対応）。
  - 環境設定ラッパ（Settings）を実装し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等をプロパティで取得可能に。
  - env と log_level の値検証（許容値のバリデーション）。

- AI（OpenAI）を用いた機能:
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに記事を統合して OpenAI（gpt-4o-mini）へバッチ送信。
    - チャンク処理（最大 20 銘柄/チャンク）、1銘柄あたり最大記事数・文字数でトリム。
    - JSON Mode を用いた応答のバリデーションとスコア ±1.0 のクリップ。
    - リトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（失敗時は該当チャンクをスキップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、executemany の空リスト回避対応）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を組み合わせて日次のレジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出はキーワードベース、LLM には gpt-4o-mini を利用して JSON 応答を期待。
    - API 呼び出しのリトライ、HTTP 5xx 判定、JSON パース失敗時のフォールバック（macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止の設計（date < target_date 等の排他条件、datetime.today() を直接参照しない）。

- データ基盤関連（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェック（quality モジュール利用想定）を行う ETLResult データクラスを提供。
    - DuckDB に対する最大日付取得等のユーティリティを実装。
  - ETLResult を外部公開（kabusys.data.etl で再エクスポート）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定・前後営業日取得・期間内営業日列挙・SQ 判定。
    - カレンダー未取得時の曜日ベースフォールバック（週末を非営業日扱い）。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得して冪等保存、バックフィル・健全性チェックを実施。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、MA200乖離）、Volatility（20日 ATR/相対ATR/平均売買代金/出来高比率）、Value（PER/ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時の None 処理、結果を date/code ベースの辞書リストで返す設計。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部依存を極力排除（標準ライブラリ + duckdb のみ）。

Changed
- （該当なし：初回リリース）

Fixed
- （該当なし：初回リリース）

Security
- OpenAI API キーは引数で注入可能（関数引数優先、未指定時は環境変数 OPENAI_API_KEY を参照）で、未設定時は ValueError を発生させることで誤設定を防止。
- .env 読み込み時に OS の既存環境変数を保護するロジックを実装（.env.local の上書き制御含む）。

Notes / Implementation details
- DuckDB に関する互換性対応（executemany に空リストを渡さないなど）を実装。
- ログ出力を多用し、API 失敗やパースエラー時に警告・情報ログを残す設計。
- ルックアヘッドバイアス防止のため、全ての「日付ベース」処理は target_date を明示的に受け取り、内部で date.today() / datetime.today() を直接参照しない方針を徹底。
- テスト容易性のため、外部 API 呼び出しポイント（OpenAI 呼び出し関数）を patch で差し替え可能にしている。

今後の予定（未実装・TODOの例）
- PBR / 配当利回り等のバリューファクター追加（現在は PER / ROE のみ）。
- monitoring モジュール等の公開 API 実装（__all__ に monitoring が含まれているが詳細実装は別途）。
- jquants_client 関連の具象実装（ここではモジュール参照を行っているが、環境に応じたクライアントの実装が必要）。

参考
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に準拠しています。