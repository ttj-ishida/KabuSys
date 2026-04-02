Keep a Changelog
=================

すべての変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠しています。

[Unreleased]

[0.1.0] - 2026-04-02
--------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- パッケージ構成:
  - 公開トップ: kabusys パッケージ（__all__ で data, strategy, execution, monitoring をエクスポート）。
- 設定・環境変数管理 (kabusys.config):
  - .env ファイルの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、行末コメント処理を考慮。
  - 上書きポリシーと protected キー（OS 環境変数保護）をサポート。
  - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 監視しきい値 / 環境（development/paper_trading/live）/ログレベルの取得と検証を行う。
  - 不足時に明示的なエラーを投げる _require ユーティリティを実装。
- AI モジュール (kabusys.ai):
  - news_nlp.score_news:
    - raw_news と news_symbols を元に銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄／回）、1銘柄あたりの記事取得数上限、テキスト長トリムを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション（JSON抽出、results 配列、code/score の型チェック、スコアクリップ）を行い、不正応答はスキップして継続するフェイルセーフ設計。
    - DuckDB の executemany 空リスト制約に配慮した idempotent な書き込み（対象コードのみ DELETE→INSERT）。
    - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない設計、ターゲット日ベースのウィンドウ計算を採用（JST→UTC 変換を内部で扱う）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出（マクロキーワードセット）→ OpenAI 呼び出し（JSON mode）→ スコア合成、閾値により 'bull'/'neutral'/'bear' ラベリング。
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理と ROLLBACK 保護。
    - OpenAI 呼び出しは専用の内部実装でモジュール結合を抑制（news_nlp と共有しない）。
  - 共通:
    - OpenAI 呼び出しは response_format={"type":"json_object"} を期待し、JSON パース失敗などはログ出力の上フォールバック。
    - 最大リトライ回数、ベース待機秒、モデル名などは定数で管理。
- データ基盤 (kabusys.data):
  - calendar_management:
    - market_calendar に基づく営業日判定ロジックを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - next/prev_trading_day は探索上限を設定（_MAX_SEARCH_DAYS）し、無限ループを防止。
    - calendar_update_job を実装し、J-Quants クライアントからの差分取得・バックフィル・健全性チェック（未来日異常検知）・冪等保存を行う。
  - pipeline / etl:
    - ETLResult データクラスを実装（ETL 実行結果の構造化: 取得/保存数、品質問題、エラー等）。
    - pipeline モジュールは差分更新、jquants_client による保存、品質チェックの統合を想定（backfill, calendar lookahead 等の設計方針実装）。
    - etl モジュールで ETLResult を再エクスポート。
  - DuckDB を用いる SQL + Python の実装方針（情報スキーマ確認 util 等）。
- Research (kabusys.research):
  - factor_research:
    - calc_momentum, calc_value, calc_volatility を実装。prices_daily / raw_financials に基づくファクター計算（mom 1/3/6 ヶ月、ma200 乖離、PER/ROE、20日 ATR、流動性指標等）。
    - SQL ウィンドウ関数を活用し、データ不足時は None を返す堅牢な実装。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD による実装、ホライズン検証）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（欠損・同順位処理含む）。
    - rank: 同順位は平均ランクを返す実装（丸め誤差対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを標準ライブラリのみで実装。
  - 研究用モジュールは外部発注 API や実口座操作を一切行わない設計。
- テスト・拡張性向けのフック:
  - OpenAI 呼び出し部分を patch/差し替え可能に設計（ユニットテストでのモック容易化）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 設計上の重要事項
- ルックアヘッドバイアス対策として、内部ロジックは target_date を明示して処理し、datetime.today()/date.today() を直接参照しない設計となっています。
- OpenAI 等外部 API が失敗した場合は原則例外を投げずフォールバック（スコア 0 やスキップ）することでパイプラインの継続性を優先しています。致命的な DB 書き込み失敗時は上位に例外を伝播します。
- DuckDB のバージョン差異（executemany の空リスト受け入れ等）に配慮した実装を行っています。
- DB への書き込みは可能な限り冪等（DELETE→INSERT 等）とし、部分失敗時に既存データを不必要に消さない工夫を行っています。

BREAKING CHANGES
- なし（初回リリース）

免責・今後の予定
- このリリースは基礎的なデータ取得・研究・AI スコアリング・カレンダー管理の機能を揃えた初期版です。将来的に以下を予定しています:
  - strategy / execution / monitoring の具体的な実装強化（発注ロジック・監視アラート等）
  - より高度な品質チェック・監査ログ機能
  - パフォーマンス改善・大規模データ向けの最適化

