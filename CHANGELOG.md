CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
主な方針：後方互換性を重視し、データ整合性（冪等性）・フェイルセーフ・テスト容易性を優先した実装になっています。

Unreleased
----------

- なし

0.1.0 - 2026-04-04
------------------

Added
- 初回リリースとして以下の主要機能を実装・公開
  - パッケージ基盤
    - パッケージ名: kabusys、バージョン: 0.1.0
    - パッケージの公開インターフェース定義（kabusys.__all__）
  - 設定管理 (kabusys.config)
    - .env ファイルおよび環境変数からの設定自動読み込みを実装
      - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD 非依存）
      - 読み込み順序: OS 環境変数 > .env.local > .env
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - .env パーサーで以下に対応
      - 空行・コメント（#）の無視
      - export KEY=VALUE 形式のサポート
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - クォート無し時のインラインコメント認識（直前が空白/タブの場合）
    - 環境変数保護機構（OS 環境変数を protected として上書きを制御）
    - Settings クラスを提供し、アプリ設定をプロパティ経由で取得
      - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境種別 等を定義
      - 必須変数未設定時は ValueError を送出する _require 実装
      - KABUSYS_ENV / LOG_LEVEL の検証と helper プロパティ（is_live / is_paper / is_dev）
  - AI（自然言語）モジュール (kabusys.ai)
    - news_nlp モジュール
      - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出
      - バッチ処理（最大 20 銘柄/コール）、記事数・文字数トリム、JSON-mode レスポンス検証を実装
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ
      - レスポンスのバリデーション・数値化・±1.0 クリップを実施
      - 結果は ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み
      - テスト用に _call_openai_api をパッチ可能（依存注入しやすい設計）
    - regime_detector モジュール
      - ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定
      - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み
      - LLM 呼び出しのフェイルセーフ（失敗時 macro_sentiment=0.0）、リトライ処理、レスポンス JSON パース保護を実装
      - ルックアヘッドバイアス対策として datetime.today() を参照しない設計（target_date ベース）
  - Research モジュール (kabusys.research)
    - factor_research
      - モメンタムファクター: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）
      - ボラティリティ/流動性: atr_20、atr_pct、avg_turnover、volume_ratio
      - バリュー: per、roe（raw_financials から最新値を参照）
      - DuckDB を用いた SQL+Python 実装。結果は (date, code) をキーとする辞書リストで返却
    - feature_exploration
      - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の fwd_* を算出
      - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関（ランクは同順位を平均ランクで処理）
      - factor_summary: 基本統計量（count, mean, std, min, max, median）
      - rank ユーティリティ: 同順位は平均ランク、浮動小数点の丸め誤差対策を実装
    - research パッケージで有用関数を再エクスポート
  - Data モジュール (kabusys.data)
    - calendar_management
      - JPX カレンダー管理（market_calendar テーブル）用ユーティリティ
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
      - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック
      - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得し冪等保存、バックフィルや健全性チェックを実装
    - pipeline / etl
      - ETLResult データクラスで ETL 実行結果を集約（品質問題とエラー一覧を含む）
      - pipeline モジュールを介して差分更新・保存・品質チェックのワークフロー設計（jquants_client 経由の保存を想定）
      - ETL の設計方針: 差分取得、バックフィル、品質チェックは Fail-Fast にせず呼び出し元で判断可能
    - DuckDB 互換性と実運用上の保護（executemany 空リスト回避など）に配慮
  - テスト/運用支援・設計
    - OpenAI 呼び出しをモジュールごとにパッチ可能（_call_openai_api を差し替え）
    - DB トランザクションでの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、ROLLBACK 保護）
    - ロギングの多用と警告/情報ログによる運用可視化
    - ルックアヘッドバイアス防止を明示的に設計文書化（target_date ベース）

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし

Security
- 環境変数読み込み時に OS の既存環境変数を保護する設計を導入（.env による誤上書きを防止）
- 必須 API キー未設定時は明示的な例外を投げて早期検出（OpenAI / J-Quants 関連）

Notes / Implementation details
- すべての外部 API 呼び出し（OpenAI / J-Quants）に対してリトライ、タイムアウト、フェイルセーフの方針を適用しています。API 失敗は基本的に局所的に処理し、システム全体を停止させない設計です（例: LLM 失敗時はスコアを 0 にフォールバック）。
- DuckDB のバージョン差異（executemany の空リストバインドの不具合等）に配慮した実装が随所にあります。
- 日付処理はすべて timezone-naive な date/datetime オブジェクトで統一し、JST/UTC の変換箇所はコメントで明示しています。
- 現時点では発注/実行（execution）やモニタリング（monitoring）モジュールは package 公開名に含まれますが、今回のコード抽出では主要な実装は Data / Research / AI / Config 側に焦点を当てています。

既知の制限・今後の改善案
- OpenAI API のレスポンス仕様や SDK の将来変更（status_code の有無等）に備えていますが、外部依存の変更によって追加の適応が必要になる可能性があります。
- news_nlp/regime_detector の LLM プロンプトやモデルは設定可能にすることで将来的な運用の柔軟性を高められます（現状は定数化）。
- DB スキーマ（prices_daily, raw_news, ai_scores, market_regime 等）は外部定義に依存するため、実運用時にはスキーマ定義書（DDL）を用意してください。

以上

（補足）本 CHANGELOG は提示されたコードから推測して作成したもので、実際のリリースノートやプロジェクト履歴とは差異がある場合があります。必要であれば、日付やカテゴリの修正・詳細追記を行います。