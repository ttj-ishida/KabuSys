CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベースから推測して付与しています。

[0.1.0] - 2026-04-01
--------------------

初期リリース（推測）。以下の主要機能・実装が含まれます。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージの公開インターフェースとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - .env（および .env.local）からの自動読み込み機能を実装（プロジェクトルートは .git あるいは pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - 複雑な .env 行のパース実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い）。
  - OS 環境変数を保護する protected 機構（.env.local による上書きは OS 環境変数を上書きしない）。
  - Settings クラスを実装し、J-Quants・kabu・Slack・DBパス・監視閾値・ログレベル・環境（development/paper_trading/live）等のプロパティを提供。未設定の必須変数は明確な ValueError をスロー。

- AI（LLM）関連
  - ニュースNLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込み。
    - チャンク処理（デフォルト最大 20 銘柄/回）、1銘柄あたり最大記事数・最大文字数でトリムする実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。API レスポンスのバリデーションとスコアの ±1.0 クリップを実装。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - _calc_ma200_ratio、マクロ記事抽出、LLM コール、スコア合成の一連処理を実装。
    - LLM 呼び出し失敗時はマクロセンチメントを 0.0 としてフェイルセーフに継続。
    - OpenAI クライアントは明示的に OpenAI(api_key=...) を生成して使用。

- データ処理 / ETL / カレンダー
  - Data モジュール
    - market_calendar を管理する calendar_management モジュールを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB の market_calendar が未取得の場合は曜日ベースのフォールバック（土日休）を行い、一貫性を保つ設計。
    - calendar_update_job: J-Quants API から差分取得 → 冪等保存、バックフィル・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を実装し、ETL 実行結果（取得数／保存数／品質問題／エラー）を集約できるようにした。
    - 差分更新・バックフィル・品質チェックを想定した設計（quality モジュールとの連携を想定）。
    - DuckDB を利用した idempotent な保存（ON CONFLICT 相当の処理を呼び出し側 jquants_client に委譲する設計）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research（因子・特徴量探索）
  - research パッケージに factor_research, feature_exploration を実装。
    - calc_momentum: mom_1m/3m/6m、ma200_dev を含むモメンタム因子を DuckDB SQL で計算。
    - calc_volatility: 20日 ATR・相対ATR・20日平均売買代金・出来高比率等のボラティリティ／流動性指標を計算。
    - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE 計算を実装（欠損時は None）。
    - calc_forward_returns: 将来リターン（horizons default [1,5,21]）を一括クエリで取得。
    - calc_ic: スピアマンランク相関（IC）を実装（十分なデータがない場合は None）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ関数。
    - 独自の rank 関数（同順位は平均ランク）を実装して外部依存を避ける。

Changed / Design decisions (明示的に記載)
- ルックアヘッドバイアス対策
  - 全ての AI/研究処理で内部的に date.today()/datetime.today() を直接参照しない設計。target_date を明示的に渡すことを前提としている（再現性確保）。
  - DB クエリは target_date 未満／以前等、排他条件を使用してルックアヘッドを防止。

- エラー処理
  - OpenAI API のエラー種別に応じたリトライ戦略（RateLimit, APIConnectionError, APITimeoutError, 5xx）を導入。非再試行エラーはスキップしてフェイルセーフに継続。
  - JSON レスポンスのパース失敗時は空スコアでフォールバックし、ワーニングログを残す。
  - DB 書き込みは明示的な BEGIN / DELETE / INSERT / COMMIT（例外時は ROLLBACK 試行）で冪等性を維持。

- テスト容易性
  - AI 呼び出しを行う内部関数（_kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）をテスト時に差し替え可能に実装。

Fixed / Robustness improvements
- .env パーサの堅牢化（export プレフィックス、クォート内のバックスラッシュ・エスケープ処理、インラインコメント取り扱い）。
- DuckDB executemany の空リストバインド制約（DuckDB 0.10）への対処：executemany 実行前に空チェックを行う。
- market_calendar の NULL 値や未登録日の扱いについて明確なログ出力とフォールバックを実装。
- API レスポンスの JSON mode でも前後に余計なテキストが混入する場合に最外の {} を抽出してパースを試みるフォールバックを実装。

Known issues / Limitations（コードから推測）
- 外部依存
  - OpenAI SDK と DuckDB に依存。実行環境にそれらが必要。
- セキュリティ / 機密
  - API キーは環境変数（OPENAI_API_KEY 等）で管理。Settings は必須キー未設定時にエラーを出すので運用側での環境設定が必須。
- スキップ動作
  - LLM 呼び出しが繰り返し失敗した場合、該当処理はスキップされる（結果として一部データが欠落する可能性がある）。これはフェイルセーフ設計のため意図的。

Notes（運用上の補足）
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的に環境変数を注入することを推奨。
- News / Regime の LLM モデルは gpt-4o-mini を想定。コスト・レイテンシ運用と照らしてバッチサイズやトークン制限を調整する必要あり。
- calendar_update_job / ETLResult / pipeline は J-Quants クライアント（jquants_client）との連携を前提としている。API レスポンス構造の変化に注意。

References
- 内部設計メモ（コード内 docstring）に則り、各モジュールは “ルックアヘッドバイアス回避”“冪等性”“フェイルセーフ” を重視して実装されています。

今後の変更例（提案）
- ai スコアの永続化に対する部分トランザクションの改善（部分失敗時のより詳細なロールバックポリシー）。
- OpenAI のレスポンススキーマ変更に備えたより厳密なスキーマ検証。
- スレッド／並列処理による API 呼び出しの最適化（レート制限対策を含む）。

以上。必要であれば、各モジュールごとの詳細な変更点（関数別の説明や想定テストケース）も作成します。