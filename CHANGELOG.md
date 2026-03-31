# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

最新リリース
------------

### 0.1.0 - 2026-03-31

初回公開リリース（ベースライン実装）。

Added
- 基本パッケージの追加: kabusys (バージョン 0.1.0)
  - パッケージ公開情報: __version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応したパーサ実装。
  - OS 環境変数を保護する「protected」扱いで .env.local による上書きを制御。
  - Settings クラスを提供（J-Quants トークン、kabu API、Slack 設定、DBパス、監視閾値、環境/ログレベル検証など）。
- AI（自然言語処理）モジュール (src/kabusys/ai)
  - ニュースセンチメント解析 (news_nlp.py)
    - OpenAI (gpt-4o-mini) を用いた銘柄別ニュースセンチメント解析。
    - JST ウィンドウ（前日 15:00 ～ 当日 08:30）を基に記事を集約し、1銘柄あたり最大記事数・文字数でトリム。
    - バッチ処理（最大 20 銘柄/回）、JSON Mode を期待したレスポンス検証、スコア ±1.0 でクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性を確保。executemany の空リスト問題（DuckDB 0.10）に配慮。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（'bull' / 'neutral' / 'bear'）。
    - prices_daily / raw_news / market_regime テーブル参照、LLM 呼び出しは OpenAI SDK を利用。API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - レジーム結果を冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
    - テスト容易性のため _call_openai_api をパッチ可能に実装（モジュール間でプライベート関数を共有しない設計）。
- Research（因子・特徴量探索）モジュール (src/kabusys/research)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Value（PER/ROE）、Volatility（20日 ATR）等の因子計算を実装。
    - DuckDB の SQL ウィンドウ関数を活用して営業日ベースの計算を行う。
    - 不足データ時は None を返す設計。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（Spearman）の計算、ランク変換、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を使わず標準ライブラリのみで実装。
- Data / ETL / カレンダー管理 (src/kabusys/data)
  - calendar_management.py
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得日は曜日ベースでフォールバックする一貫した設計。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - pipeline.py / etl.py
    - ETLResult（dataclass）を公開。ETL 実行結果・品質問題・エラーを集約して返す設計。
    - 差分取得、保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）を想定したインターフェース。
  - jquants_client と quality への参照（実装は別モジュールとして利用を想定）。
- 設計上の注意点（全体）
  - datetime.today() / date.today() の直接参照を回避し、関数は引数で target_date を受け取ることでルックアヘッドバイアスを防止。
  - DuckDB を主要なローカル DB として利用（クエリは SQL ベース、executemany の取り扱いに配慮）。
  - OpenAI 呼び出しは例外・パースエラーに対する堅牢なフォールバックを持つ（例外を全て投げずにスキップ/0.0 として継続）。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Deprecated
- 初回リリースにつき該当なし。

Removed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。

Known issues / 注意事項
- src/kabusys/data/pipeline.py の末尾にある内部関数 _get_max_date の実装が途中で切れている（ファイル末尾の "return date.fro" で終わっており、明らかなタイプミス／未完了コードが存在）。このままでは当該モジュールの実行時にエラーが発生する可能性が高いです。修正が必要です。
- __init__.py の __all__ に execution / monitoring が含まれますが、今回提示されたスニペット内にそれらの実装ファイルは含まれていません。これらは別途実装または追加配置が必要です。
- OpenAI API の利用には OPENAI_API_KEY が必須。news_nlp.score_news / regime_detector.score_regime は api_key 引数または環境変数でキーを渡す必要があります（未設定時は ValueError を送出）。
- DuckDB バージョン依存の挙動（executemany の空配列バインドなど）に注意。現実の運用では DuckDB バージョンに応じた互換検証が必要です。

今後の改善案（提案）
- pipeline.py の未完部分・型安全性の向上とユニットテスト整備。
- execution / monitoring サブパッケージの実装（プロセス制御・監視アラートの実装）。
- OpenAI 呼び出しのレート制御、コスト最適化（ローカルモデルや軽量分類器の導入検討）。
- E2E テスト用のモックデータセットと CI での DuckDB 初期化スクリプト整備。

---

本 CHANGELOG は、提示されたソースコードから推測可能な機能実装・設計意図および明示的な問題点を元に作成しています。実際のリリースノートとして使用する場合は、ソース管理履歴（git コミット）や実運用での差分を確認の上、日付・修正箇所を確定してください。