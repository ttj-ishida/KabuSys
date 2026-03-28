CHANGELOG
=========
すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
    - パッケージの公開 API として data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを提供。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してルートを特定（CWD に依存しない）。
  - .env パーサ実装:
    - コメント行 / 空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応して正しく値を復元。
    - クォートなしの値でインラインコメント（#）を扱う際の細かな判定。
  - .env 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - Settings クラスを提供し、必須設定取得（_require）・デフォルト値・バリデーション（KABUSYS_ENV / LOG_LEVEL 等）を実装。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH）、Slack / Kabu ステーション / J-Quants のトークン等を扱うプロパティを提供。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとに記事を結合し、OpenAI (gpt-4o-mini) の JSON Mode で一括センチメント評価。
    - 時間ウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST 相当) を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/コール）、記事数上限・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンス検証ロジック（JSON 復元、results 配列チェック、コード一致チェック、数値検証、±1.0 クリップ）を実装。
    - 書き込みは部分置換 (DELETE → INSERT) により部分失敗時の既存データ保護を実現。
    - 公開 API: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルに冪等書き込み。
    - OpenAI 呼び出しのリトライ・バックオフ実装、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レスポンスの JSON パース失敗や API エラーに対する堅牢なハンドリング。
    - 公開 API: score_regime(conn, target_date, api_key=None)
  - 共通設計:
    - OpenAI 呼び出しはモジュール毎に専用のラッパーを持たせており、テスト用に patch で差し替え可能。
    - datetime.today() / date.today() を内部ロジックで参照せず、外部から target_date を渡す形でルックアヘッドバイアスを回避。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research モジュール:
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA 乖離）を calc_momentum で計算。データ不足時は None を返す。
    - ボラティリティ・流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を calc_volatility で計算。
    - バリュー: PER（EPS が 0 または欠損時は None）・ROE を raw_financials と prices_daily から calc_value で取得。
    - 関数はすべて DuckDB 接続を受け取り、DB だけを参照（外部 API へはアクセスしない）。
  - feature_exploration モジュール:
    - 将来リターン計算 calc_forward_returns（horizons デフォルト [1,5,21]、入力バリデーションあり）。
    - IC（Spearman の ρ）計算 calc_ic：ランク変換、同順位処理、最小レコード数チェックを実装。
    - ランク関数 rank は同順位を平均ランクにし、丸め誤差対策を実装。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）を提供。
  - research パッケージのトップレベル再エクスポートを整備（zscore_normalize など）。

- データ基盤 (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定・次/前営業日取得・期間内営業日取得・SQ日判定のユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（週末除外）でフォールバックする一貫した挙動。
    - next_trading_day / prev_trading_day は最大探索日数制限(_MAX_SEARCH_DAYS) を設けて無限ループを防止。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETLResult データクラスを提供し（取得件数・保存件数・品質問題・エラー等を保持）、to_dict メソッドで品質問題の要約を出力可能。
    - 差分取得・バックフィル・品質チェックとの連携方針を実装（設計仕様）。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得などを実装。
  - jquants_client / quality 等のクライアントモジュールとのインタフェースを想定した実装。

- テストと運用を想定した安全策
  - DuckDB の executemany に対する互換性考慮（空リストでの呼び出し回避）。
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT 構成で冪等性を確保し、例外時は ROLLBACK を試行して上位に再送出。
  - ロギングを多用し、失敗時には情報を残す（warning / info / exception を適切に使用）。

Changed
- 初版リリースのため変更履歴はありません。

Fixed
- 初版リリースのため修正履歴はありません。

Security
- 初版リリースのためセキュリティ関連の個別修正はありませんが、API キーは明示的に引数または環境変数（OPENAI_API_KEY）で解決する設計としており、自動ロードやログの取り扱いに注意する必要があります。

Notes / 備考
- OpenAI との呼び出しは外部サービス依存のため、実運用では API キー管理・レート制限・課金に関する運用ルールの整備を推奨します。
- .env 自動読み込みは開発便利機能だが、本番環境での動作を明確にするため KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを用意しています。
- 本リリースは内部設計（ルックアヘッドバイアス回避、トランザクション保護、レスポンスバリデーション等）に重点を置いた初版実装です。将来的に API 仕様・DB スキーマの拡張に伴い互換性が変わる可能性があります。

将来の変更提案（例）
- news_nlp / regime_detector の LLM モデル切替や並列化（パフォーマンス改善）。
- ETL の監視ダッシュボード用メトリクスの追加。
- カバレッジ向上のためユニットテスト・統合テストの充実と CI 設定。

--- 
（この CHANGELOG はコードベースから推測して生成しています。実際のコミット履歴やリリースノートと合わせて調整してください。）