Keep a Changelog に準拠した形式で、提示されたコードベースから推測して作成した CHANGELOG.md（日本語）を以下に示します。

※注: 日付および一部の記述はコード内容から推測したものであり、実際のリリース履歴とは異なる可能性があります。

---------------------------------------------------------------------
CHANGELOG
=====================================================================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

Unreleased
---------------------------------------------------------------------
（現在の開発中の変更点や次回リリースに含める予定の事項をここに記載）

0.1.0 - 2026-03-28
---------------------------------------------------------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ名: kabusys
  - バージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルおよび環境変数から設定を自動で読み込む仕組みを実装
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD 非依存）
  - .env パーサ実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ処理に対応）
  - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - OS 環境変数を保護するための上書きロジック（.env.local は override=True、ただし既存の OS 環境変数は保護）
  - Settings クラスを提供し、以下のプロパティで設定値を取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live を検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL を検証）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）で銘柄別センチメントを評価
    - バッチ処理（1回あたり最大 _BATCH_SIZE=20 銘柄）
    - 入力トリム: 1銘柄あたり最大記事数(_MAX_ARTICLES_PER_STOCK=10)、最大文字数(_MAX_CHARS_PER_STOCK=3000)
    - JSON Mode を利用し、厳密な JSON 解析・バリデーションを実施
    - 再試行／バックオフ: 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ
    - レスポンス検証ロジック: results 配列の存在チェック、コード整合、スコア数値変換、±1.0 でクリップ
    - テスト容易性: _call_openai_api をパッチ差し替え可能（unittest.mock.patch）

  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定
    - マクロキーワードで raw_news タイトルを抽出（最大 _MAX_MACRO_ARTICLES=20）
    - OpenAI（gpt-4o-mini）を使った macro_sentiment 評価（JSON 出力を期待）
    - ロバストネス: API エラー時は macro_sentiment=0.0 にフォールバック
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）

  - 設計方針（AI モジュール共通）
    - datetime.today() / date.today() を直接参照せず、target_date を引数として受けてルックアヘッドバイアスを排除
    - OpenAI クライアント生成時に api_key を引数から注入できる（テストや CI での注入を想定）
    - 非同期ではなく同期的な API 呼び出しと明示的な retry/backoff

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存（jquants_client の save_* を使用）、品質チェック（quality モジュール）を組み合わせた ETLResult データクラスを提供
    - backfill_days による再取得、最小データ日付 _MIN_DATA_DATE の定義、カレンダー先読み設定等の実装
    - DuckDB を用いた最大日付取得ユーティリティとテーブル存在チェック
    - ETLResult.to_dict() で品質問題をシリアライズ可能

  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使用した営業日判定・次前営業日取得・期間内営業日列挙・SQ 判定を実装
    - DB にカレンダーがない場合は曜日（平日）ベースのフォールバックを使用
    - calendar_update_job: J-Quants API からの差分取得と保存（バックフィル、健全性チェックを実装）
    - 市場カレンダーが一部しかない場合でも一貫した判定を返す設計（DB 値優先、未登録は曜日フォールバック）
    - 探索上限 (_MAX_SEARCH_DAYS) により無限ループを防止

  - ETL 公開インターフェース（kabusys.data.etl）
    - pipeline.ETLResult を再エクスポート

- 研究用モジュール（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）を DuckDB 上で算出
    - データ不足時に None を返す仕様、営業日を想定した horizons 実装、SQL ベースでの計算
  - feature_exploration
    - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ファクター統計サマリー、ランク化ユーティリティを実装
    - pandas 等外部依存を持たない純 Python 実装（標準ライブラリ + duckdb）

- 共通設計上の注意点 / テスト向け機能
  - 多くの関数は target_date を受け取り deterministic に動作する（ルックアヘッドバイアス回避）
  - OpenAI 呼び出し部は内部関数をパッチ可能にして単体テストを容易化
  - DuckDB に対する書き込みは基本的に冪等（DELETE→INSERT 等）を意識

Security
- 環境変数のロードに際し OS 環境変数は保護される（.env が意図せず上書きしない）
- 機密情報（API トークン等）は Settings で必須チェックを行い、未設定時は ValueError を発生させる

Known limitations / Notes
- data パッケージの __init__ は空（将来的な公開 API 整備が想定される）
- calc_value では現時点で PBR・配当利回りは未実装（メモとして明記）
- 全体として OpenAI（gpt-4o-mini）に依存。API 利用には OPENAI_API_KEY が必要
- OpenAI のレスポンスや API 仕様変更に備えてフォールバックを用意しているが、完全な保証はない
- DuckDB 特有の executemany の空リスト問題に対する回避コードを実装（互換性確保）

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

---------------------------------------------------------------------
今後の改善案（参考）
- news_nlp と regime_detector の共通処理（OpenAI 呼び出し・JSON 抽出）の共通化検討（現在は意図的に別実装）
- 非同期 API 呼び出しにして並列化（大量銘柄処理の高速化）
- データベースマイグレーションスキーマと初期化ユーティリティの追加
- telemetry / メトリクス収集（API レイテンシ・エラー率の可視化）
- エンドツーエンドの統合テストケース（OpenAI モックや DuckDB fixture を利用）

---------------------------------------------------------------------
本 CHANGELOG はコードから推測して作成しています。実際のコミット履歴やリリースノートを反映する場合は、
git のログやリリース時の差分をもとに追記・修正してください。