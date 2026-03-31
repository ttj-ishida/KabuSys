# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョン: 0.1.0（初回リリース）。日付はリポジトリの現日時（2026-03-31）を使用しています。

## [Unreleased]

### Known issues / TODO
- data.pipeline モジュールのソースが途中で切れている箇所があり（`_get_max_date` 関数の戻り処理が未完了）、ETL パイプライン実行の一部ロジックが不完全な可能性があります。リファクタ／補完が必要です。
- strategy / execution / monitoring の実装ファイルはパッケージの公開インターフェースに含まれる一方で、現状コードベース内で完全な実装が確認できない箇所があります（将来の追加予定）。

---

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - パッケージ公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local を自動読み込み（プロジェクトルート判定は .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサーは `export KEY=val`、クォート（' "）とバックスラッシュエスケープ、インラインコメント、コメント行（#）などに対応。
  - 環境設定のラッパ Settings クラスを提供（J-Quants、kabu API、Slack、データベースパス、監視閾値、ログレベル、環境種別などのプロパティを定義）。
  - 環境変数検査（必須変数が未設定の場合は明確な ValueError を送出）、KABUSYS_ENV と LOG_LEVEL のバリデーション。

- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - ニュース記事を銘柄単位に集約して OpenAI（gpt-4o-mini の JSON Mode）へバッチ送信し、銘柄ごとのセンチメント ai_score を計算して ai_scores テーブルへ冪等的に書き込む機能を実装。
    - タイムウィンドウ計算（JST→UTC 変換）を行う calc_news_window を提供。
    - バッチサイズ、記事数上限、文字数トリムなどのトークン肥大化対策を実装。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフ、レスポンス検証（JSONパース、結果構造、スコア型チェック）、スコアの ±1.0 クリップを実装。
    - DuckDB 互換性を考慮した executemany の空リスト回避や、部分失敗時に既存スコアを保護する更新戦略（DELETE→INSERT）を実装。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）に対応。

  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込む機能を実装。
    - ma200_ratio 計算（target_date より前のデータのみ使用してルックアヘッドバイアスを防止）。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼出しのリトライ処理、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - 合成スコアのクリッピングとしきい値によるラベリングを実装。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT を用いた冪等処理で安全に行う。

- Data モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを扱うユーティリティ群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が存在しない場合は曜日ベース（平日）でフォールバックする一貫したロジック。
    - calendar_update_job による J-Quants からの差分取得、バックフィル、健全性チェック（極端な未来日付の検出）を実装。
    - DB 登録値優先、未登録日は曜日フォールバックというポリシーで一貫した探索結果を返す。

  - ETL / Pipeline（src/kabusys/data/pipeline.py、src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラーの集約、has_errors / has_quality_errors / to_dict を提供）。
    - 差分更新、backfill、品質チェックの方針を備えた ETL パイプラインの骨組みを実装（jquants_client 経由での取得・保存、quality チェックとの連携）。
    - etl モジュールで ETLResult を再エクスポート。

- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム、ボラティリティ、バリュー系ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio
      - calc_value: PER, ROE（raw_financials の最新レコードを参照）
    - DuckDB SQL を活用した高効率集計。データ不足時は None を返す設計。

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（営業日）に対する将来リターンの計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関による IC（Information Coefficient）計算。必要なレコード数が不足する場合は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を返す。
    - rank: 同順位を平均ランクにするランク関数を提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- Failsafe / 設計上の配慮
  - ルックアヘッドバイアス防止: 各種処理で datetime.today() / date.today() の乱用を避け、target_date を明示的に受け取る設計を採用。
  - OpenAI 呼び出しのリトライ、サーバーエラー判定（status_code の有無に対応）、およびフォールバックの実装。
  - DuckDB のバージョン差異に配慮した実装（executemany の空パラメータ回避など）。

### Changed
- 初回リリースにつき該当なし（ベース実装の追加が中心）。

### Fixed
- 初回リリースにつき該当なし。

### Removed
- 初回リリースにつき該当なし。

### Security
- API キーの取り扱いは環境変数優先で、明示的な引数注入をサポートすることでテスト性と秘匿性を考慮。

---

注記:
- 各モジュールの実装にはログ出力（logging）と十分なエラーハンドリングが組み込まれていますが、一部モジュール（data.pipeline）の未完了・未検証箇所があるため、運用前に統合テスト・単体テストを推奨します。
- OpenAI / J-Quants / kabu API など外部 API に依存する処理は、実行環境で対応する環境変数（APIキー等）の設定が必要です。