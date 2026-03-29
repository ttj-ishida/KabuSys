Changelog
=========

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース。パッケージメタ情報:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 公開モジュール: data, strategy, execution, monitoring
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 複雑な .env 行解析に対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、コメント処理）。
  - OS 環境変数を保護する protected オプションによる上書き制御。
  - 必須設定取得ユーティリティ _require と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、実行環境・ログレベル判定等）。
  - KABUSYS_ENV / LOG_LEVEL の検証と is_live/is_paper/is_dev プロパティを実装。
- AI 関連機能 (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを取得。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたり記事数/文字数の上限、429・ネットワーク・5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score の検証、スコアクリップ）を実装。
    - スコア書き込みは部分失敗時に既存データを保護する DELETE→INSERT の冪等性を確保。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - prices_daily / raw_news / market_regime を参照し、計算後に冪等的に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロキーワードでニュースをフィルタ、OpenAI 呼び出しは専用実装でモジュール間結合を抑制。
    - API エラー・パースエラー時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - リトライ・バックオフとエラーハンドリングを実装。
- データプラットフォーム周り (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→保存。
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。データが無い場合は曜日（平日）でフォールバック。
    - 最大探索日数やバックフィル、健全性チェック（極端に未来の last_date を検出した場合のスキップ）を導入。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを実装して ETL 実行結果を集約（取得数、保存数、品質問題、エラー一覧等）。
    - 差分更新、バックフィル、品質チェックとの連携を想定した設計を反映。
    - jquants_client 経由の idempotent 保存・品質チェックの集約方針を文書化。
- リサーチ用ユーティリティ (src/kabusys/research)
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等のファクター計算を実装。DuckDB SQL ベースで効率的に取得。
    - データ不足時は None を返す等の堅牢な設計。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（任意ホライズン）、IC（Spearman の rank 相関）計算、rank/統計サマリーを実装。外部依存を使わず標準ライブラリのみで実装。
  - research パッケージ __all__ に主要関数をエクスポート。
- data.stats からの zscore_normalize の再エクスポート（src/kabusys/research/__init__.py）。

Changed
- なし（初回リリース）

Fixed
- トランザクション失敗時の安全なロールバック処理を強化（news_nlp, regime_detector, pipeline）。ROLLBACK 失敗のログ出力対応。
- OpenAI 呼び出しの多様な失敗パターン（429/タイムアウト/ネットワーク/5xx/非5xx APIError/JSON パースエラー）を想定したリトライとフォールバック動作を各モジュールで実装。
- DuckDB の executemany の空パラメータ制約に対応するため、書き込み前に空チェックを追加（ai_scores への書き込み等）。

Deprecated
- なし

Removed
- なし

Security
- 環境変数の読み込み処理で OS 環境変数を保護する仕組みを導入（.env 上書き時に既存 OS 環境変数を保持）。
- 必須 API キー未設定時には明示的に ValueError を投げ、誤った運用を回避（OpenAI, Slack, Kabu API 等）。

Notes / 設計上の重要点
- ルックアヘッドバイアス防止:
  - 各モジュール（news_nlp, regime_detector, research 等）は datetime.today() / date.today() を内部参照せず、呼び出し側が target_date を明示的に渡す設計。
  - DB クエリは target_date 未満／以前の条件を厳格にして未来データの混入を防止。
- テスト性:
  - OpenAI 呼び出し部分は内部関数として分離され、unittest.mock.patch による差し替えが可能（テストのモック化を容易に）。
- フェイルセーフ:
  - 外部 API 失敗時には例外を投げずにフォールバック（0.0 やスキップ）して処理を継続する設計が多く採用されている（運用時の連続稼働重視）。
- DuckDB を主要なローカル分析 DB として利用。SQL と Python の混在で高速に集計・ウィンドウ関数を活用。

今後の予定（例）
- ai モジュールのスコア保存のさらなるメタデータ化（confidence, raw_response 等）
- ETL のスケジューラ統合・監視向け通知（Slack 通知など）
- strategy / execution モジュールの実装拡張（現在はパッケージ名で公開済み）

以上。リリースに関する不明点や本文の表現修正希望があればご指示ください。