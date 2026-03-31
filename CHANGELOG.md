# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

- リリース履歴はセマンティックバージョニングに従います。  
- 日付はリリース日を示します。

## [0.1.0] - 2026-03-31

Added
- パッケージ初期リリース。kabusys の基本モジュール群を追加。
  - パッケージ公開情報: src/kabusys/__init__.py（__version__ = "0.1.0", __all__ に data/strategy/execution/monitoring を公開）
- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込みの優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメント処理などの堅牢なパース。
  - Settings クラスを実装し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）や既定値（KABU_API_BASE_URL、データベースパス等）、閾値（CPU/MEM/DISK）を提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値に基づく ValueError を投げる）。
- AI 関連（src/kabusys/ai/*）
  - ニュースセンチメント解析モジュール（news_nlp.py）
    - raw_news と news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini、JSON mode）でバッチスコアリングを行い ai_scores テーブルへ書き込む。
    - バッチ処理、チャンクサイズ、トークン肥大化対策（記事数 / 文字数トリム）、最大リトライ、指数バックオフを実装。
    - レスポンスバリデーション（JSON 抽出、results 配列、コード一致、スコア数値化、有限値チェック）と ±1.0 でのクリップ。
    - テスト容易性のため API 呼び出し関数を差し替え可能に実装（unittest.mock.patch 用フック）。
    - DuckDB の executemany が空リストを受け付けないという互換性を考慮した処理（書き込み前に空チェック）。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して利用（ルックアヘッドバイアスを避ける設計）。
  - 市場レジーム判定モジュール（regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに日次で保存。
    - OpenAI を利用したマクロセンチメントスコアリング（gpt-4o-mini、JSON mode）。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - API エラーや JSON パース失敗時はフェイルセーフとして macro_sentiment=0.0 を採用。リトライ・バックオフ実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE WHERE date=? → INSERT → COMMIT）、失敗時は ROLLBACK と例外伝播。
    - ルックアヘッドバイアス防止方針を明確に注記（date 引数依存、date.today() を参照しない）。
- データ処理・研究ツール（src/kabusys/data/*, src/kabusys/research/*）
  - ETL パイプライン基盤（data/pipeline.py, data/etl.py）
    - ETLResult データクラスを導入し、取得数・保存数・品質チェック結果・エラー概要を集約可能に。
    - 差分取得、バックフィル戦略、品質チェック連携（quality モジュール）を想定した設計。
    - DuckDB 上のテーブル存在チェック等のユーティリティを提供。
  - マーケットカレンダー管理（data/calendar_management.py）
    - market_calendar を用いた営業日判定ロジックと夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック（週末除外）、next/prev/get_trading_days の一貫性保持。
    - J-Quants クライアント経由の差分取得と冪等保存を行う設計（バックフィル日数、異常検知の健全性チェックを実装）。
  - 研究用ファクター計算（research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）を DuckDB の SQL と Python で計算。
    - データ不足時の None 返却やログ出力、範囲スキャンのバッファ設計を実装。
  - 特徴量探索・統計ユーティリティ（research/feature_exploration.py）
    - 将来リターン計算（horizons の柔軟指定、範囲チェック、単一クエリ取得）。
    - IC（Spearman の ρ）計算、ランク化ユーティリティ（同順位は平均ランク）、ファクターの統計サマリー（count/mean/std/min/max/median）。
    - 外部依存なし（pandas 等非依存）、数値の有限性チェックや ties 考慮の実装。
- 内部ユーティリティ・互換性考慮
  - DuckDB の挙動（executemany の空リスト不可、日付の取り扱い）を考慮した実装。
  - ログ出力（情報・警告・例外）の一貫化。
  - 各モジュールで「ルックアヘッドバイアスを避ける」実装ポリシーを明確化。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / Implementation decisions（備考）
- OpenAI との対話は JSON mode（response_format={"type": "json_object"}）を利用し厳密な JSON を期待するが、実際の運用で前後テキストが混入するケースを考慮して復元ロジックを実装。
- API 呼び出し周りはテストのため差し替え可能（モックパッチポイントを意図的に用意）。
- LLM 呼び出し失敗時は例外を直接上げずフェイルセーフ値（0.0 など）で継続する設計を採用。外部 API の不安定性に耐性を持たせる方針。
- 全日時処理は date / naive UTC datetime を明示して扱い、タイムゾーン混入を避ける（ニュース窓は JST→UTC に変換して DB 比較に使用）。
- settings の必須値チェックにより、起動時に環境変数の不足があれば早期に検出できる。

今後の予定（候補）
- strategy / execution / monitoring モジュールの実装・公開（__all__ に記載済み）。
- テストカバレッジの拡充（特に OpenAI 呼び出しロジックと DuckDB 相互作用）。
- パフォーマンス改善（ETL の並列化・バッチ最適化）および監視アラートの強化。

--- 

（この CHANGELOG はコード内のドキュメントと実装内容から推測して作成しています。実際のコミット履歴に基づく細かい差分とは異なる可能性があります。）