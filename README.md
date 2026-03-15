# KabuSys

日本株向けの自動売買（アルゴリズムトレード）システムの骨組み（スケルトン）プロジェクトです。各コンポーネントを分離して設計しており、実際の取引APIや戦略を組み込んで拡張できるようになっています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、以下の4つの主要コンポーネントで構成される自動売買フレームワークの基盤です。

- data: 市場データの取得／整形
- strategy: 売買戦略（アルゴリズム）
- execution: 注文発行・約定処理
- monitoring: ログ、メトリクス、アラート等の監視機能

現状はパッケージの基本構成のみを提供しており、各モジュールを実装してシステムを完成させるための出発点となります。

---

## 機能一覧

- パッケージ骨組み（モジュール分割と公開API）
- バージョン情報管理（`kabusys.__version__`）
- 将来的な拡張を容易にするモジュール分離（data / strategy / execution / monitoring）

（注）現状は実装が入っておらず、上記は設計上の想定機能です。各機能は必要に応じて実装してください。

---

## セットアップ手順

必要条件:
- Python 3.8 以上（プロジェクトの要件に合わせて調整してください）
- git

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリディレクトリ>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 開発用インストール（編集可能モード）
   プロジェクトルートに `setup.py` や `pyproject.toml` がある場合:
   ```
   pip install -e .
   ```
   なければ、直接パッケージをインポートして使えます（PYTHONPATH を通すか、スクリプトから相対パスで参照）。

4. 依存パッケージのインストール
   - このテンプレートには外部依存が定義されていません。実装に応じて `requirements.txt` や `pyproject.toml` を作成し、`pip install -r requirements.txt` などで追加してください。

---

## 使い方

基本的な利用例（骨組みの確認や拡張のためのサンプル操作）:

- パッケージのインポートとバージョン確認
```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

- 各モジュールの雛形（例）
  - data: 市場データ取得クラスを実装
  - strategy: 戦略クラス（シグナル生成）
  - execution: 注文実行クラス（取引所APIとの接続）
  - monitoring: ログ・メトリクス出力

簡単な戦略のスケルトン例:
```python
# src/kabusys/strategy/simple.py
class SimpleStrategy:
    def __init__(self, data_provider, executor):
        self.data = data_provider
        self.exec = executor

    def on_tick(self, market_snapshot):
        # 市場データを見てシグナルを生成
        if self._should_buy(market_snapshot):
            self.exec.place_order(symbol="7203", side="BUY", qty=100)

    def _should_buy(self, snapshot):
        # シンプルな例: 常にFalse（実装はユーザが行う）
        return False
```

運用の流れの例:
1. data モジュールでティッカーや板情報を取得
2. strategy モジュールでシグナルを生成
3. execution モジュールで注文を送信・管理
4. monitoring モジュールでログ・通知・ダッシュボード表示

※ 実際の注文やAPIキーの管理・秘密情報は安全に実装してください（環境変数・シークレットストアの利用等）。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ（現状の構成）:
```
src/
  kabusys/
    __init__.py            # パッケージ定義（__version__ など）
    data/
      __init__.py          # 市場データ関連の実装を置く
    strategy/
      __init__.py          # 戦略関連の実装を置く
    execution/
      __init__.py          # 注文実行関連の実装を置く
    monitoring/
      __init__.py          # 監視・ログ関連の実装を置く
```

将来的には以下のようなファイルを追加する想定です:
- data/providers.py, data/cache.py
- strategy/base.py, strategy/examples.py
- execution/client.py, execution/order_manager.py
- monitoring/logger.py, monitoring/metrics.py

---

## 開発メモ・注意点

- 本リポジトリは「骨組み」です。実際に稼働させる場合は取引所API（例: kabu.com API 等）との接続、APIキー管理、エラーハンドリング、リスク管理、テスト、監査ログなどを必ず実装・検証してください。
- 実トレードを行う前に、必ずペーパートレードやバックテストで戦略の検証を行ってください。
- セキュリティ上の理由から、APIキーや認証情報はソース管理に含めないでください。環境変数やシークレットマネージャを利用してください。

---

必要であれば README に含めるサンプル実装や CI / テスト手順、設定ファイル例（例: config.yaml、.env の扱い方）も作成できます。どの部分を重点的に整備したいか教えてください。