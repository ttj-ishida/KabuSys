Keep a Changelog 準拠の CHANGELOG.md（日本語）を下記に作成しました。コードから推測できる追加機能、設計方針、既知の制約やフェイルセーフ挙動などを項目化しています。

CHANGELOG.md
=============
全体方針
---------
- このファイルは Keep a Changelog フォーマットに従っています。
- バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------
- なし（今後の変更をここに記載してください）

[0.1.0] - 2026-03-28
-------------------
Added
- パッケージ初期リリース（kabusys 0.1.0）
  - パッケージ名: KabuSys - 日本株自動売買システム

- 環境設定・ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD非依存）
    - 読み込み順序: OS環境変数 > .env.local > .env
    - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装（引用符・エスケープ・行コメント対応、export KEY= 形式対応）
  - 上書き制御および protected キー（OS環境変数の保護）対応
  - Settings クラスを提供し、必要な設定プロパティを公開
    - J-Quants / kabu API / Slack / DB パス等のプロパティ
    - env（development/paper_trading/live）と log_level のバリデーション
    - duckdb/sqlite のデフォルトパス設定

- AI 関連機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini）でセンチメントスコアを算出
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して比較）
    - バッチ処理: 最大 20 銘柄/回のバッチ送信、1 銘柄あたり記事数と文字数でトリム
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフ実装
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット、既知コードのみ採用、数値チェック）
    - スコアは ±1.0 にクリップ
    - テスト容易性: OpenAI 呼び出し部分をモック差替可能（_call_openai_api）
    - DB 書込は冪等（DELETE → INSERT）で、部分失敗時に既存スコアを保護

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し
      市場レジーム（bull/neutral/bear）を日次で判定、market_regime テーブルへ保存
    - マクロニュース抽出は keywords ベース（日本・米国などのマクロ用キーワード列挙）
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない）でテスト差替え対応
    - API 失敗時は macro_sentiment を 0.0 としてフェイルセーフに継続
    - DB 書込はトランザクション（BEGIN/DELETE/INSERT/COMMIT）、失敗時に ROLLBACK を行い上位へ例外伝播

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 登録値優先、未登録日は曜日ベース（週末）でフォールバックする一貫したロジック
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants から差分取得→保存）
    - バックフィル（直近 _BACKFILL_DAYS）は常に再フェッチ、健全性チェックによる未来日付異常検出
    - 最大探索制限（_MAX_SEARCH_DAYS）で無限ループ防止

  - ETL パイプライン（kabusys.data.pipeline / data.etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーの集約）
    - 差分更新方針、バックフィル日数、品質チェックを想定した設計
    - jquants_client と quality モジュールを統合してデータ取得/保存/品質チェックを行う設計（実装は jquants_client に依存）

- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - Value（PER、ROE を raw_financials から取得）
    - DuckDB 上の SQL を活用した効率的な実装、データ不足時の None 処理
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（スピアマンのランク相関）計算（3 レコード未満は None）
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - ランク関数（同順位は平均ランク、浮動小数の丸めで ties を扱う）
  - 研究用関数は外部依存（pandas 等）なしで実装

- パッケージ構成とエクスポート
  - 主要モジュールを __all__ 等で再エクスポート（research, ai 等）
  - data.etl は pipeline.ETLResult を再エクスポート

Changed
- 初版リリースにつき該当なし（将来のバージョンで差分を記載）

Fixed
- 初版リリースにつき該当なし

Known limitations / Notes
- DuckDB を前提とする設計（DuckDB API のバインディングやバージョン差異に依存）
  - DuckDB 0.10 の executemany の空リスト制約を考慮した実装あり
- OpenAI（gpt-4o-mini）を JSON mode で利用、稀な出力ノイズに対する JSON 抽出ロジックを実装しているが
  完全な安全性は保証しない（バリデーションで不正レスポンスはスキップ）
- 時刻処理はルックアヘッドバイアス防止のため date/target_date ベースで実装（datetime.today() を直接参照しない）
- .env パーサは一般的なケースに対応（引用符・エスケープ・インラインコメント）するが、極端に複雑な .env 構成では差異が生じる可能性あり
- 一部 API 呼び出しは外部サービス（OpenAI / J-Quants / kabuAPI）に依存するため、API キーやネットワークが必要
- 失敗時はフェイルセーフで処理を継続する設計（API 呼び出し失敗時はスコア 0.0 や対象スキップ等）で、外部障害がシステム全体停止に繋がらないようにしている

Security
- 環境変数の自動ロード時に既存 OS 環境変数を protected として保護する仕組みを実装
- 必須設定が未設定の場合は明示的に ValueError を発生させる（誤設定の早期検出）

参考（実装上の工夫）
- OpenAI 呼び出し関数をモジュール内で分離しており、ユニットテストでは patch による差し替えが可能
- DB 書込みは冪等（DELETE→INSERT、トランザクション制御）で再実行可能にしている
- 各モジュールは「外部への副作用（発注 API 等）を持たない」＝研究／スコア算出は安全に実行可能な設計

今後の改善案（提案）
- ai.news_nlp / ai.regime_detector の結果に対する監査ログ出力・サンプル保存
- モデル選択・温度などのモデルパラメータを設定で外部化
- jquants_client / kabu API クライアントのモック提供による CI 環境での統合テスト強化
- metrics / observability（モニタリングメトリクス）の追加

以上です。必要であれば、日付や細かい表現を修正してバージョン履歴のフォーマットを調整します。