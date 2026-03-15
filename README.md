# KabuSys

日本株自動売買システム (KabuSys)

バージョン: 0.1.0

KabuSys は日本株の自動売買を目的とした軽量なフレームワークです。市場データ取得、売買戦略、注文実行、モニタリングといった各責務を分離した構造を想定しており、独自戦略の実装や実行環境への組み込みを容易にします。

---

## 主な機能（予定 / 想定）

- データ取得（market data / historical data）の取得ラッパー
- 売買戦略（シグナル生成、インジケータ計算など）のプラグイン化
- 注文実行（発注、取消、約定管理、リスク管理）
- モニタリング（ログ、アラート、簡易ダッシュボード）
- テスト用モック・シミュレーションモードのサポート

注: 現在のリポジトリはパッケージ骨組み（モジュール構成）を提供しています。各モジュールは必要に応じて実装・拡張してください。

---

## セットアップ手順

以下は開発環境向けの基本的なセットアップ手順です。プロジェクトに requirements.txt や pyproject.toml があれば適宜読み替えてください。

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成して有効化（推奨）
   - macOS / Linux
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存関係をインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - まだない場合は、必要なパッケージを手動でインストールしてください（例: requests, pandas, numpy 等）。

4. 開発インストール（オプション）
   ```
   pip install -e .
   ```

5. 環境変数 / 設定ファイルの準備
   - 外部 API を利用する場合は API キー等を設定してください（例: KABU_API_KEY, KABU_API_SECRET）。
   - config.yaml / .env 等で設定を管理することを推奨します。

---

## 使い方（サンプル）

現状はモジュールの骨組みになっているため、まずは簡単な確認や拡張の流れ例を示します。

- パッケージのバージョン確認
  ```python
  import kabusys
  print(kabusys.__version__)  # 0.1.0
  ```

- モジュールの拡張例（戦略モジュールを実装する雛形）
  - ファイル: src/kabusys/strategy/simple_strategy.py
    ```python
    class SimpleStrategy:
        def __init__(self, data_client, execution_client, config=None):
            self.data = data_client
            self.exec = execution_client
            self.config = config or {}

        def on_tick(self, tick):
            # tick: 価格情報等
            # シンプルな売買ロジックを実装
            if self._buy_condition(tick):
                self.exec.place_order(symbol=tick['symbol'], side='BUY', qty=100)
            elif self._sell_condition(tick):
                self.exec.place_order(symbol=tick['symbol'], side='SELL', qty=100')

        def _buy_condition(self, tick):
            # 条件判定
            return False

        def _sell_condition(self, tick):
            return False
    ```

- 実行の流れ（概念）
  1. data クライアントで市場データを購読 / 取得
  2. strategy がデータを解析しシグナルを生成
  3. execution が注文を送信・管理
  4. monitoring がログ / 状態を可視化

各コンポーネント（data, strategy, execution, monitoring）はインターフェースを統一して実装するとテストや差し替えが容易になります。

---

## ディレクトリ構成

現状の主要ファイル/ディレクトリ構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py                # パッケージ定義（バージョン等）
    - data/
      - __init__.py              # データ取得関連モジュール
    - strategy/
      - __init__.py              # 売買戦略関連モジュール
    - execution/
      - __init__.py              # 注文実行関連モジュール
    - monitoring/
      - __init__.py              # ログ・監視関連モジュール

README 等のドキュメントやサンプルコードはプロジェクトルートに追加してください。

---

## 実装・拡張のガイドライン（推奨）

- 各レイヤーは責務を分離する
  - data: データ取得（API/ファイル/シミュレーション）に集中
  - strategy: シグナル生成に集中（状態の保存は最小限）
  - execution: 発注ロジック、注文管理、例外処理、レート制限
  - monitoring: ログ、メトリクス、アラート

- テスト
  - 各レイヤーはモック可能なインターフェースを用意して単体テストを行う
  - シミュレーション環境を用意して E2E テストを実施することを推奨

- セキュリティ
  - API キーや秘密情報はソース管理に含めない（.gitignore で除外）
  - 本番環境の取引で使用する前に十分な検証を行う

---

## 貢献・ライセンス

- 貢献歓迎します。Issue / Pull Request を通じて提案ください。
- ライセンスはプロジェクトルートに LICENSE ファイルを追加してください（例: MIT）。

---

必要があれば、以下を作成して README を充実させます:
- requirements.txt / pyproject.toml のテンプレート
- サンプル戦略・データクライアントの実装例
- CI / テスト設定（pytest, GitHub Actions 例）
どの情報を追加したいか教えてください。