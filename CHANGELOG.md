CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース。KabuSys 日本株自動売買システムの基本コンポーネントを追加。
  - パッケージ公開:
    - パッケージトップ: kabusys（__version__ = 0.1.0）
    - 公開モジュール群: data, strategy, execution, monitoring（__all__）
  - 環境設定管理:
    - kabusys.config.Settings クラスを追加。環境変数経由でアプリケーション設定を取得（J-Quants、kabu API、Slack、DBパス、環境種別、ログレベルなど）。
    - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - .env パーサを独自実装。export プレフィックス、引用符付き値、インラインコメント処理、保護された OS 環境変数の上書き制御に対応。
    - 必須環境変数未設定時は _require 関数で明確な ValueError を送出。
  - AI（NLP）モジュール:
    - kabusys.ai.news_nlp: ニュース記事を集約して OpenAI (gpt-4o-mini) を使って銘柄毎のセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウ計算（JST基準の前日15:00～当日08:30 を UTC に変換）機能を実装（calc_news_window）。
      - バッチ処理（最大20銘柄/チャンク）、トークン肥大対策（記事数・文字数制限）、レスポンス検証、±1.0 クリップ、部分的な DB 置換（DELETE→INSERT）による冪等性を実現。
      - API リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、失敗時はスキップして継続するフェイルセーフ設計。
      - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch で _call_openai_api をモック可能）。
    - kabusys.ai.regime_detector: ETF(1321)の200日移動平均乖離とマクロニュースの LLM センチメントを合成し、日次市場レジーム（bull/neutral/bear）を market_regime テーブルへ冪等書き込みする処理を実装。
      - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用、データ不足時は中立値1.0でフォールバック）。
      - マクロニュース抽出（キーワードリスト）、LLM スコアリング（gpt-4o-mini）、重み付け合成（70%/30%）と閾値判定。
      - API リトライ方針、エラー時は macro_sentiment=0.0（フェイルセーフ）。
  - Data（データ基盤）モジュール:
    - calendar_management: JPX カレンダー管理（market_calendar）・営業日判定・next/prev_trading_day・get_trading_days・is_sq_day を実装。DB にデータがない場合は曜日ベースでフォールバックする一貫したロジックを採用。
      - calendar_update_job により J-Quants API から差分取得→冪等保存（ON CONFLICT の想定）を行う。バックフィルや健全性チェックを備える。
    - pipeline / etl:
      - ETLResult データクラスを公開（ETL のフェッチ・保存件数、品質チェック結果、エラー一覧の集約）。
      - ETL パイプライン設計方針を実装（差分取得、backfill、品質チェックの集約報告、id_token 注入によるテスト容易性）。
    - jquants_client を利用した差分取得/保存の呼び出し箇所を想定（実装は外部モジュールに委任）。
  - Research（リサーチ）モジュール:
    - ファクター計算（kabusys.research.factor_research）を提供:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
      - calc_value: raw_financials から EPS/ROE を取得して PER/ROE 計算。
      - いずれも DuckDB の prices_daily / raw_financials のみを参照し、実際の発注等には影響しない分離設計。
    - feature_exploration:
      - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）を一度のクエリで取得。
      - calc_ic: スピアマンのランク相関（IC）計算。
      - rank, factor_summary: ランク変換・統計サマリーのユーティリティを追加。
  - 互換性/運用上の配慮:
    - DuckDB の executemany の制約に合わせた空リスト回避の実装。
    - 日付はすべて datetime.date / naive UTC を想定し timezone の混入を避ける設計。
    - テスト容易性のため外部 API 呼び出しは差し替え可能に実装（内部関数を明示的に分離）。

Changed
- （初版のため「変更」はなし）

Fixed
- （初版のため「修正」はなし）

Deprecated
- なし

Security
- なし

注意事項・運用メモ
- OpenAI API:
  - API キーは api_key 引数で注入可能（テスト用）か、環境変数 OPENAI_API_KEY を利用。未設定の場合は ValueError を送出して明示的に失敗する。
  - LLM 呼び出しはレート制限・ネットワーク障害・5xx に対するリトライを実装しているが、最終的に失敗した場合は該当チャンク/記事をスキップして処理を継続する（フェイルセーフ）。
- .env 自動ロード:
  - パッケージ初期化時にプロジェクトルートが検出されると .env を自動的に読み込みます。テスト時や特殊用途では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- DuckDB の挙動:
  - DuckDB 0.10 系への互換性を考慮して、executemany に空リストを渡さない等の実装上の工夫を行っています。
- ルックアヘッドバイアス:
  - AI スコアリングやレジーム判定、ファクター計算の全てで datetime.today()/date.today() を直接参照しない設計（外部から target_date を与える）により、ルックアヘッドバイアスを排除しています。
- テスト設計:
  - OpenAI 呼び出しや時間依存処理はモックしやすい実装になっています（内部 _call_openai_api や時間取得の分離など）。

将来の作業候補（TODO / 予定）
- strategy / execution / monitoring の具象実装とテストの追加（現在はパッケージエントリとして存在）。
- ai モジュールの応答フォーマット強化および追加の品質ゲート（信頼度評価等）。
- ETL パイプラインの詳細実装（スケジューリング、監査ログ、リアルタイム差分処理）。
- ドキュメント（API リファレンス、運用マニュアル、デプロイ手順）の整備。

----
END OF CHANGELOG