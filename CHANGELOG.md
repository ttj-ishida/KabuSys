CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]: https://example.com/compare/HEAD...HEAD

0.1.0 - 2026-03-27
------------------

Added
- 初回リリース。KabuSys 日本株自動売買システムの基本モジュールを実装。
  - パッケージ公開情報
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__に準備）
  - 設定管理
    - .env ファイルおよび環境変数の自動読み込み機能を実装（src/kabusys/config.py）。
      - プロジェクトルート検出（.git や pyproject.toml を基準）により CWD 非依存でロード。
      - .env / .env.local を読み込み、OS 環境変数を保護する override/protected ロジック。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
      - export KEY=val、クォートやエスケープ、行内コメントなど多様な .env フォーマットに対応。
      - Settings クラスで必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）をプロパティ経由で取得。値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - AI（自然言語処理）
    - ニュースセンチメント: score_news（src/kabusys/ai/news_nlp.py）
      - raw_news / news_symbols を集約して銘柄ごとのニュースを作成。
      - OpenAI（gpt-4o-mini）を JSON Mode でバッチ呼び出し（最大 20 銘柄／チャンク）。
      - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフを実装。
      - レスポンス検証・パース耐性（前後余計テキストから JSON 抽出）。
      - スコアは ±1.0 にクリップ。取得成功銘柄のみ ai_scores テーブルに置換（DELETE→INSERT）して部分失敗時の既存データ保護。
      - テスト用に _call_openai_api を差し替え可能な設計。
    - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
      - prices_daily, raw_news を参照し、結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - LLM 呼び出しは最大リトライ、API失敗時は macro_sentiment=0.0 とするフェイルセーフ。
      - ルックアヘッドバイアス防止のため datetime.today() を参照せず target_date 未満のデータのみを使用。
  - Research（因子計算・特徴量探索）
    - factor_research（src/kabusys/research/factor_research.py）
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials と当日株価から PER、ROE を計算。
      - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials を参照。欠損時の None 戻し等に対応。
    - feature_exploration（src/kabusys/research/feature_exploration.py）
      - calc_forward_returns: 将来リターン（デフォルト [1,5,21] 営業日）を計算（LEAD を使用）。
      - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（コードマッピングと None 排除、最小有効件数チェック）。
      - rank: 同順位は平均ランクを返す実装（丸めで ties を安定化）。
      - factor_summary: count/mean/std/min/max/median の統計サマリを計算。外部依存なしで実装。
    - research パッケージの public API を __init__ で公開。
  - Data（データ基盤）
    - calendar_management（src/kabusys/data/calendar_management.py）
      - JPX カレンダー操作ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
      - market_calendar の有無に応じた DB優先/曜日フォールバックロジック。
      - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
      - 最大探索日数制限による無限ループ防止。
    - pipeline / ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
      - ETLResult データクラスを実装し ETL の収集メトリクス・品質問題・エラー一覧を保持。
      - 差分更新、backfill、品質チェックの設計方針を反映したユーティリティの骨子。
    - jquants_client と質チェックモジュール（参照用）との連携点を用意。
  - その他
    - DuckDB をメインのローカル分析 DB として利用する設計（多くの機能が DuckDB 接続を引数に取る）。
    - ロギング（logger）を各モジュールで利用し、重要情報・警告・例外を記録する設計。
    - テストフレンドリーな設計（OpenAI 呼び出しの差し替えポイント、環境変数読み込みの無効化フラグ等）。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Security
- 環境変数の自動読み込みで既存の OS 環境変数を保護する protected ロジックを導入。
- 必須環境変数が未設定の場合は明示的な ValueError を発生させて誤動作を防止（Settings の各プロパティ）。

Notes / Implementation details
- OpenAI との対話は gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）で厳格な JSON 出力を期待する設計。ただし実運用でのパース耐性（前後余計テキスト抽出等）を備えている。
- LLM 呼び出し回りはネットワーク障害やレートリミットに備えたリトライ・バックオフを実装しており、最終的にフェイルセーフ値を使って継続する方針（例: macro_sentiment=0.0）。
- ルックアヘッドバイアス対策として、すべての日付基準処理は外部から渡す target_date を使い、内部で datetime.today()/date.today() を参照しないよう統一。
- DuckDB の executemany に空リストを渡せない点への回避（空チェック）や、DB 書き込みの冪等性（DELETE→INSERT、ON CONFLICT 想定）などの運用上の配慮を実装。

今後のTODO（想定）
- monitoring / execution / strategy モジュールの実装および統合テスト
- jquants_client の具体実装と ETL の実稼働確認
- モデル・プロンプトのチューニング、OpenAI 利用のコスト/レイテンシ最適化
- ドキュmentation、型注釈の拡充、CI/テストカバレッジの強化

----------------------------------------
（本 CHANGELOG はコード内容から推測して作成した想定の変更履歴です）